"""Any transformers defined in the transformation config in the section
"custom_transformation_method" need to be added to this module in the
class that is associated with data type.

valid data types are described in constants.VALID_TRANSFORM_TYPES
"""


import logging
import constants
import sys
import os.path
import inspect
import optparse
import json

# pylint: disable=logging-format-interpolation

LOGGER = logging.getLogger(__name__)

class MethodMapping:
    """used to glue together the method name described in the transformation
    config file and the method that will be described in this module
    """
    def __init__(self, dataType, customMethodNames):
        self.dataType = dataType
        self.customMethodNames = customMethodNames
        self.validate()

    def validate(self):
        # verify that the datatype is in the valid data types defined in the
        # transform_types
        self.validateTransformerType()
        self.validateTransformerClass()
        self.validateTransformerMethods()

    def validateTransformerType(self):
        if self.dataType not in constants.VALID_TRANSFORM_TYPES:
            msg = (
                f"when attempting to map the the data type {self.dataType} " +
                f"with the methods: ({self.customMethodNames}), discovered that " +
                "the datatype is invalid"
            )
            LOGGER.error(msg)
            raise InvalidCustomTransformation(msg)

    def validateTransformerClass(self):

        # make sure there is a class in this module that aligns with the datatype
        classesInModule = self.getClasses()
        if self.dataType not in classesInModule:
            msg = (
                "you defined the following custom transformations methods: " +
                f"({self.customMethodNames}) for the data type: {self.dataType} " +
                " however there is no class in the " +
                f"{os.path.basename(__file__)} module for that data type."
            )
            LOGGER.debug(msg)
            raise InvalidCustomTransformation(msg)

    def validateTransformerMethods(self):
        # finally make sure the custom transformation method exists.
        # creating an object of type 'self.datatype'
        obj = globals()[self.dataType]()
        # getting the methods
        methods = inspect.getmembers(obj, predicate=inspect.ismethod)
        # extracting just the names of the methds as strings
        methodNames = [i[0] for i in  methods]
        print(f'method names: {methodNames}')
        for customMethodName in self.customMethodNames:
            if customMethodName not in methodNames:
                msg = (
                    f'The custom method name {customMethodName} defined in the ' +
                    f"transformation config file for the data type {self.dataType}" +
                    " does not exist"
                )
                raise InvalidCustomTransformation(msg)

        # validate that the method has the expected custom method name
        LOGGER.debug(f"methods: {methods}")

    def getClasses(self):
        clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
        clsNameAsStr = []
        for cls in clsmembers:
            if cls[0] in constants.VALID_TRANSFORM_TYPES:
                clsNameAsStr.append(cls[0])
        print(clsNameAsStr)
        return clsNameAsStr

    def getCustomMethodCall(self, methodName):
        obj = globals()[self.dataType]()
        method = getattr(obj, methodName)
        return method

# names of specific classes need to align with the names in
# constants.VALID_TRANSFORM_TYPES
class packages:
    def __init__(self):
        self.customTransformations = []

    def packageTransform(self, inputDataStruct):
        """ The custom transformer with misc logic to be applied to packages

        :param inputDataStruct: input data struct that will be sent to the api,
            this stuct will be modified and returned by this method.
        :type inputDataStruct: dict
        """
        LOGGER.debug("packageTransform has been called")
        if isinstance(inputDataStruct, list):
            iterObj = range(0, len(inputDataStruct))
        else:
            iterObj = inputDataStruct

        for iterVal in iterObj:
            print(f"iterval in custom method: {iterVal}")
            # individual update record referred to: inputDataStruct[iterVal]
            inputDataStruct[iterVal] = self.fixResourceStatus(inputDataStruct[iterVal])
            inputDataStruct[iterVal] = self.fixDownloadAudience(inputDataStruct[iterVal])
            #inputDataStruct[iterVal] = self.fixMoreInfo(inputDataStruct[iterVal])
            inputDataStruct[iterVal] = self.fixSecurityClass(inputDataStruct[iterVal])

        return inputDataStruct

    def fixSecurityClass(self, record):
        """ The security class for a dataset must be one of the following:
           * HIGH-CABINET
           * HIGH-CLASSIFIED
           * HIGH-SENSITIVITY
           * LOW-PUBLIC
           * LOW-SENSITIVITY
           * MEDIUM-PERSONAL
           * MEDIUM-SENSITIVITY

        HIGH-CONFIDENTIAL -> HIGH-CLASSIFIED
        not in set -> HIGH-SENSITIVITY

        :param record: [description]
        :type record: [type]
        """
        validSecurityClasses = ['HIGH-CABINET', 'HIGH-CLASSIFIED', 'HIGH-SENSITIVITY',
            'LOW-PUBLIC', 'LOW-SENSITIVITY', 'MEDIUM-PERSONAL', 'MEDIUM-SENSITIVITY']
        defaultClass = 'HIGH-SENSITIVITY'
        if ('security_class' in record) and record['security_class']:
            if record['security_class'] not in validSecurityClasses:
                if record['security_class'] == 'HIGH-CONFIDENTIAL':
                    record['security_class'] = 'HIGH-CLASSIFIED'
                else:
                    record['security_class'] = 'HIGH-SENSITIVITY'
        return record

    def fixResourceStatus(self, record):
        """ Records that have their properties 'resource_status' set to
        'historicalArchive' MUST also have a 'retention_expiry_date' date set.

        This method checks for this condition, modifies the record so it is
        compliant and returns the modified version.

        :param record: input package data struct that will be sent to the api
        :type record: dict
        """
        if ('resource_status' in record) and record['resource_status'] == \
                'historicalArchive' and 'retention_expiry_date' not in record:

            record['retention_expiry_date'] = "2222-02-02"
        return record

    def fixDownloadAudience(self, record):
        """download_audience must be set to something other than null,
        if the download_audience is found to be set to null, will set to
        "Public"

        :param record: The input record (json struct) that is to be updated
        :type record: dict
        """
        validDownloadAudiences = ["Government", "Named users",  "Public"]
        defaultValue = "Public"
        if "download_audience" in record:
            if record["download_audience"] is None:
                record["download_audience"] = defaultValue
            elif record["download_audience"] not in validDownloadAudiences:
                record["download_audience"] = defaultValue

        return record

    def fixMoreInfo(self, record):
        """if its empty ie:
            [
                {
                    "link": "",
                    "delete": "0"
                }
            ]
        then don't bother stringy.

        removed this param from the transconf
        ...
            "stringified_fields": [
                "more_info"
            ],
        ...

        :param record: [description]
        :type record: [type]
        """
        if ('more_info' in record) and record['more_info']:
            moreInfo = record['more_info']
            if len(moreInfo) == 1 and isinstance(moreInfo, list):
                if moreInfo[0]['link']:
                    record['more_info'] = json.dumps(moreInfo)
        return record

class InvalidCustomTransformation(Exception):
    def __init__(self, message):
        LOGGER.error(message)
        self.message = message



if __name__ == '__main__':
    methMap = MethodMapping('packages', ['packageTransform'])
    func = methMap.getCustomMethodCall('packageTransform')
    print("calling the custom method")
    func()


