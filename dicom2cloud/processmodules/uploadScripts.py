""" Classes for uploading to the various cloud services for processing.

Copyright 2017 The Clinic2Cloud Team
Licence: BSD 2-Clause
"""

# Libraries for AWS
import boto3
from botocore.errorfactory import ClientError as botoClientError
# Libraries for google cloud
from google.cloud import storage as gstorage

from dicom2cloud.config.dbquery import DBI


class uploadBase:
    """ Base class for uploads. """

    def __init__(self, uid):
        self.uid = uid
        self.db = DBI()
    
    def upload(self, uploadFilename, processingOptions):
        """ Create a new bucket and upload blobs for the file and options.

        @param uploadFilename       MINC file to be uploaded.
        @param processingOptions    String with processing options.
        """
        pass

    def isDone(self):
        """ Poll the status of the submitted job. """
        pass

    def download(self, downloadFilename):
        pass

    # TODO - polls status of job - ?to implement
    def poll(self):
        """

        :return:
        """
        return True

class uploadGoogle(uploadBase):
    """ Upload to a google cloud instance. """

    def __init__(self, uid):
        uploadBase.__init__(self, uid)
        if self.db.c is None:
            self.db.connect()
        configfile = self.db.getServerConfigByName('GOOGLE_CONFIGFILE')
        self.db.closeconn()
        self.storage_client = gstorage.Client.from_service_account_json(configfile)
        self.bucket = None

    def upload(self, uploadFilename, processingOptions):
        uploadBase.upload(self, uploadFilename, processingOptions)

        # Create a new bucket with the uid
        self.bucket = self.storage_client.create_bucket(self.uid)

        # Upload the file to be processed
        blobInput = self.bucket.blob('inputFile.mnc')
        blobInput.upload_from_filename(uploadFilename)

        # Upload the processing options into a string
        blobOpts = self.bucket.blob('options.dat')
        blobOpts.upload_from_string(processingOptions)

    def isDone(self):
        """ Poll the status of the submitted job. """
        uploadBase.poll(self)

        if self.bucket is None:
            self.bucket = self.storage_client.get_bucket(self.uid)

        blobDone = self.bucket.blob('done')
        return blobDone.exists()

    def download(self, downloadFilename):
        uploadBase.download(self, downloadFilename)

        if self.bucket is None:
            self.bucket = self.storage_client.get_bucket(self.uid)

        # Download output
        blobOutput = self.bucket.blob('output.tar')
        blobOutput.download_to_filename(downloadFilename)

        # Cleanup resources
        self.bucket.delete(force=True)

class uploadAws(uploadBase):
    """ Upload to a AWS instance. """

    def __init__(self, uid):
        uploadBase.__init__(self, uid)
        if self.db.c is None:
            self.db.connect()
        ACCESS_KEY = self.db.getServerConfigByName('AWS_ACCESS_KEY')
        SECRET_KEY = self.db.getServerConfigByName('AWS_SECRET_KEY')
        self.db.closeconn()

        # Create a client for the connection
        self.client = boto3.client('s3',
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY)

    def upload(self, uploadFilename, processingOptions):
        uploadBase.upload(self, uploadFilename, processingOptions)

        # TODO: This should be in its own bucket or have its own uid

        # Upload the file to be processed
        self.client.upload_file(uploadFilename,
                'clinic-to-cloud', 'magnitude.nii')

        # TODO: Upload the processing options

    def isDone(self):
        """ Poll the status of the submitted job. """
        uploadBase.poll(self)

        bucket = 'clinic-to-cloud-processed'
        key = 'magnitude_processed.nii.gz'

        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except botoClientError:
            return False

    def download(self, downloadFilename):
        uploadBase.download(self, downloadFilename)

        bucket = 'clinic-to-cloud-processed'
        key = 'magnitude_processed.nii.gz'

        # Download the result
        self.client.download_file(bucket, key, downloadFilename)

        # Cleanup resources
        self.client.delete_object(Bucket=bucket, Key=key)

class uploadNectar(uploadBase):
    """ Upload to a Nectar Cloud instance. """

    def __init__(self, uid):
        uploadBase.__init__(self, uid)

    def upload(self, uploadFilename, processingOptions):
        uploadBase.upload(self, uploadFilename, processingOptions)
        # TODO

    def isDone(self):
        """ Poll the status of the submitted job. """
        uploadBase.poll(self)
        # TODO

    def download(self, downloadFilename):
        uploadBase.download(self, downloadFilename)
        # TODO

def get_class(name):
    """ Get a class from a string name. """
    uploaders = {'google': uploadGoogle,
                 'aws': uploadAws,
                 'nectar': uploadNectar,
                 'none': None
                 }
    if name not in uploaders.keys():
        raise Exception('Unknown class name: {}'.format(name))
    return uploaders[name]



