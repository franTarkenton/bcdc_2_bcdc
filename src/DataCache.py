"""
used to cache data that is read from the api.  CKAN objects can have relationships
to other objects. For example a group or organization relates to different users,
or a package can be owned by an organization

This class is developed on an as needed basis to help store and retrieve these
relationships

"""
import constants
import logging
import CKANTransform
import CKAN

LOGGER = logging.getLogger(__name__)

# pylint: disable=logging-format-interpolation

class DataCache:
    """
    <description>:
        used to maintain a lookup data struct so that autogenerated unique ids
        can be quickly translated between source and destination.

        for example the field owner_org refers to a auto generated unique id for
        the organization... so owner_org is a value that related to id in an
        organization object

        This class maintains the following data structure to allow the remapping
        of autogen ids to take place.

    <autogen field>: This is the auto generated field name on the source side
                     that a lookup is being maintained for.  Fields that this
                     class maintains lookups for are described in the
                     transformation config file in the section: field_mapping

                     Because there can be more than one field mapping maintained
                     per object type, the field_name is the first key in the
                     data struct.

    <data type>    : data type  or object type is the type of data that the
                     mapping is defined for.  Typical data types in ckan include
                     users, groups, organizations, packages and resources.

    <data origin>  : Identifies if the data comes from the source CKAN instance
                     or the destination ckan instance.  Valid values for
                     this parameter are identified in the enumeration:
                     constants.DATA_SOURCE

    <autogen field value>: This is a value that exists in the column described in
                     the parameter above <autogen field>

    <value>         : all of the above identify a hierarchical data structure that
                     ultimately resolves to this value, which contains the user
                     generated unique id for the record that can be identified
                     by the value in the parameter <autogen field value>

    a specific example where the transformation config file contains the
    following fieldmapping values:

    ....
      "field_mapping": [
            {
                "user_populated_field": "name",
                "auto_populated_field": "id"
            }
    ...

    self.cacheStruct['id']['organizations']['src']['2dfjksdfjwlji8hfzkioeihfsl'] = 'BCGOV_organization'

    'id' is the autogenerated field name
    'organizations' is the object that contains the field 'id'
    'src' means we are describing values from the source CKAN instance
    '2dfjksdfjwlji8hfzkioeihfsl' is an example of a value that is found in the column 'id'
    'BCGOV_organization' is the user generated unique id that corresponds with the
        autogenerated unique id '2dfjksdfjwlji8hfzkioeihfsl'

    destination objects generally follow the same pattern bug destination objects
    flip the last entry and the value, example:

    self.cacheStruct['id']['organizations']['dest']['BCGOV_organization'] = 'klsdjjfonvuweoiisdfxoi3o89kjsk'

    The struct can now easily translate the autogen id for the org BCGOV_organization
    from 2dfjksdfjwlji8hfzkioeihfsl on the source side to klsdjjfonvuweoiisdfxoi3o89kjsk
    on the destination side.

    :raises inValidDataType: [description]
    :return: [description]
    :rtype: [type]
    """
    def __init__(self):
        self.transConf = CKANTransform.TransformationConfig()
        self.cacheLoader = CacheLoader()

        # example struct for source:
        #    struct['id']['organization']['src']['2dfjksdfjwlji8hfzkioeihfsl'] = 'BCGOV_organization'

        # example struct for dest:
        #    self.cacheStruct['id']['organizations']['dest']['BCGOV_organization'] = 'klsdjjfonvuweoiisdfxoi3o89kjsk'
        self.cacheStruct = {}
        self.reverseStruct = {}

    def initCacheStruct(self, autoGenFieldName):
        """inits the data struct for a mapping field.  Sets up the struct
         to allow for easier population of the struct

        :param autoGenFieldName: [description]
        :type autoGenFieldName: [type]
        """
        structs2Init = [self.cacheStruct, self.reverseStruct]
        for struct2Init in structs2Init:
            if autoGenFieldName not in struct2Init:
                struct2Init[autoGenFieldName] = {}
            for dataType in constants.VALID_TRANSFORM_TYPES:
                if dataType not in struct2Init[autoGenFieldName]:
                    struct2Init[autoGenFieldName][dataType] = {}
                    for dataOrigin in constants.DATA_SOURCE:
                        # translated to with example
                        # <field_name>, id
                        #     <datatype>, organizations
                        #         <data origin>, src
                        if dataOrigin not in struct2Init[autoGenFieldName][dataType]:
                            struct2Init[autoGenFieldName][dataType][dataOrigin] = {}

    def addData(self, dataSet, dataOrigin):
        """reads the data in the source dataset populating the cache for
        that data type, allowing for rapid translation of autogen fields between
        instances.

        :param srcDataSet: an input CKANDataSet object for a source ckan instance
        :type srcDataSet: CKANData.CKANDataSet
        :param dataOrigin: is the data from src || dest
        :type dataOrigin: str
        """
        if not isinstance(dataOrigin, constants.DATA_SOURCE):
            msg = (
                "An invalid dataOrigin type was provided.  The type provided "
                + f"is {type(dataOrigin)}.  This is not "
                + "a valid type for this parameter, must be a constants.DATA_SOURCE type"
            )
            raise inValidDataType(msg)
        dataType = dataSet.dataType
        fieldmaps = self.transConf.getFieldMappings(dataType)

        for fieldmap in fieldmaps:
            autoGenFieldName = fieldmap[constants.FIELD_MAPPING_AUTOGEN_FIELD]
            userGenFieldName = fieldmap[constants.FIELD_MAPPING_USER_FIELD]

            self.initCacheStruct(autoGenFieldName)

            dataSet.reset()
            LOGGER.info("Caching auto vs user unique ids")

            for ckanRecord in dataSet:
                autoGenFieldValue = ckanRecord.getFieldValue(autoGenFieldName)
                userGenFieldValue = ckanRecord.getFieldValue(userGenFieldName)

                if dataOrigin == constants.DATA_SOURCE.SRC:
                    self.cacheStruct[autoGenFieldName][dataType][dataOrigin][
                        autoGenFieldValue
                    ] = userGenFieldValue
                    self.reverseStruct[autoGenFieldName][dataType][dataOrigin][
                        userGenFieldValue
                    ] = autoGenFieldValue
                elif dataOrigin == constants.DATA_SOURCE.DEST:
                    self.cacheStruct[autoGenFieldName][dataType][dataOrigin][
                        userGenFieldValue
                    ] = autoGenFieldValue
                    self.reverseStruct[autoGenFieldName][dataType][dataOrigin][
                        autoGenFieldValue
                    ] =  userGenFieldValue

    def addRawData(self, rawData, dataType, dataOrigin):
        """[summary]

        :param rawData: a list of objects with properties
        :type rawData: list of dict
        :param dataType: a CKAN object type or data type, users, orgs, groups ...
        :type dataType: str
        :param dataOrigin: the data orgin enumeration
        :type dataOrigin: constants.DATA_SOURCE
        """

        fieldmaps = self.transConf.getFieldMappings(dataType)

        for record in rawData:
            for fieldmap in fieldmaps:
                autoGenFieldName = fieldmap[constants.FIELD_MAPPING_AUTOGEN_FIELD]
                userGenFieldName = fieldmap[constants.FIELD_MAPPING_USER_FIELD]

                autoGenFieldValue = record[autoGenFieldName]
                userGenFieldValue = record[userGenFieldName]

                self.initCacheStruct(autoGenFieldName)
                # cacheStruct[autoGenFieldName][dataType][dataOrigin.name] = {}
                if dataOrigin is constants.DATA_SOURCE.SRC:
                    self.cacheStruct[autoGenFieldName][dataType][dataOrigin][autoGenFieldValue] = userGenFieldValue
                elif dataOrigin is constants.DATA_SOURCE.DEST:
                    self.cacheStruct[autoGenFieldName][dataType][dataOrigin][userGenFieldValue] = autoGenFieldValue

    def addRawDataSingleRecord(self, singleRecord, dataType, dataOrigin, autoGenFieldName, identifier):
        #   (singleRecord, dataType, dataOrigin, autoFieldName, dataValue)
        """Using the identifier parameter makes a query to the CKAN api retrieving
        the data for a particular object type.

        :param singleRecord: The returned data that needs to be added to the data
            cache.
        :type singleRecord: dict
        :param dataType: the type of data that is being returned
        :type dataType: str in constants.VALID_TRANSFORM_TYPES
        :param dataOrigin: is the data source or destination
        :type dataOrigin: constants.DATA_SOURCE
        :param identifier: a name or id value that is used to uniquely identify
            the record allowing it to be retrieved.
        :type identifier: unique id, either user generated or autogenerated.
        """
        # read the fieldmap and extract the auto vs user gen unique id data:
        fieldmaps = self.transConf.getFieldMappings(dataType)
        for fieldmap in fieldmaps:
            tmpAutoFldName = fieldmap[constants.FIELD_MAPPING_AUTOGEN_FIELD]
            tmpUserFldName = fieldmap[constants.FIELD_MAPPING_USER_FIELD]
            if tmpAutoFldName == autoGenFieldName:
                break

        userGenFieldValue = singleRecord[tmpUserFldName]
        autoGenFieldValue = singleRecord[tmpAutoFldName]

        if dataOrigin is constants.DATA_SOURCE.SRC:
            self.cacheStruct[autoGenFieldName][dataType][dataOrigin][autoGenFieldValue] = userGenFieldValue
        elif dataOrigin is constants.DATA_SOURCE.DEST:
            self.cacheStruct[autoGenFieldName][dataType][dataOrigin][userGenFieldValue] = autoGenFieldValue

    def isDatatypeLoaded(self, objType, autoFieldName):
        """returns boolean to identify the specified data type has been loaded

        :param objType: the object type as defined in constants.VALID_TRANSFORM_TYPES
        :type objType: str
        :param autoFieldName: The name of the field in 'objType' that should be
             loaded / cached
        :type autoFieldName: str
        """
        retVal =  False
        if autoFieldName in self.cacheStruct:
            # cacheStruct['id']['object type'] needs to exist, and also needs
            # to have something other than empty dicts in it for both src and dest.
            if (objType in self.cacheStruct[autoFieldName]) and \
                    self.cacheStruct[autoFieldName][objType][constants.DATA_SOURCE.SRC] and \
                    self.cacheStruct[autoFieldName][objType][constants.DATA_SOURCE.DEST]:
                retVal = True
        return retVal

    def loadData(self, objType, autoFieldName):
        """When a record is requested, this method will get called to see if the
        data for the datatype has already been loaded, if not then it will make
        the appropriate calls to the api to load it.

        :param dataType: [description]
        :type dataType: [type]
        """
        if not self.isDatatypeLoaded(objType, autoFieldName):
            self.cacheLoader.loadType(self, objType, autoFieldName)

    def loadSingleDataSet(self, objType, dataOrigin, autoFieldName, userDefinedValue):
        # objType, constants.DATA_SOURCE.DEST, autoFieldName, srcUserValue
        """recieving the data origin or data source, looks up the autgenerated
        value that aligns with the userdefined value.

        :param objType: the data type
        :type objType: str
        :param dataOrigin: the source type, SRC|DEST
        :type dataOrigin: constants.DATA_SOURCE
        :param userDefinedValue: the value that aligns with the user defined field
            for this datatype
        :type userDefinedValue: str
        """
        self.cacheLoader.loadSingleValue(self, objType, dataOrigin, autoFieldName, userDefinedValue)

    # def idValueExistsInDest(self, autoFieldName, objType, autoValue):
    #     retVal = False
    #     userValue = self.getDestUserDefValueFromAutoId(autoFieldName, objType, autoValue)
    #     if userValue:
    #         retVal = True
    #     return retVal

    # def getDestUserDefValueFromAutoId(self, autoFieldName, objType, autoValue):
    #     retVal = None
    #     # srcUserValue = self.cacheStruct[autoFieldName][objType][constants.DATA_SOURCE.SRC][autoValue]
    #     dataPointer = self.cacheStruct[autoFieldName][objType][constants.DATA_SOURCE.DEST]
    #     for userDefKey in dataPointer:
    #         if dataPointer[userDefKey] == autoValue:
    #             retVal = dataPointer[userDefKey]
    #             break
    #     return retVal

    def isAutoValueInDest(self, autoFieldName, objType, autoValue):
        retVal = False
        if autoValue in self.reverseStruct[autoFieldName][objType][constants.DATA_SOURCE.DEST]:
            retVal = True
            #LOGGER.debug(f"The {autoFieldName} value {autoValue} exists in the DEST object ")
        return retVal

    def isAutoValueInSrc(self, autoFieldName, objType, autoValue):
        retVal = False
        #  self.cacheStruct['id']['organizations']['dest']['BCGOV_organization'] = 'klsdjjfonvuweoiisdfxoi3o89kjsk'
        # reverse is auto to user
        # cache is user to auto
        #if autoValue in self.reverseStruct[autoFieldName][objType][constants.DATA_SOURCE.SRC]:
        if autoValue in self.cacheStruct[autoFieldName][objType][constants.DATA_SOURCE.SRC]:
            retVal = True
            LOGGER.debug(f"The {autoFieldName} value {autoValue} exists in the SRC object ")
        return retVal

    def getUserDefinedValue(self, autoFieldName, autoValue, userDefinedFieldName,
            objType, origin=constants.DATA_SOURCE.SRC):
        """for a given autogenerated value, uses the lookup to retrieve
        the corresponding user defined value

        :param autoFieldName: [description]
        :type autoFieldName: [type]
        :param autoFieldValue: [description]
        :type autoFieldValue: [type]
        """
        # creating pointers to the correct struct to use to translate a autogen
        # id value into a usergen id value.
        if origin == constants.DATA_SOURCE.SRC:
            struct = self.cacheStruct
        elif origin == constants.DATA_SOURCE.DEST:
            struct = self.reverseStruct

        self.loadData(objType, autoFieldName)
        if autoValue in struct[autoFieldName][objType][origin]:
            userValue = struct[autoFieldName][objType][origin][autoValue]
        return userValue

    def src2DestRemap(self, autoFieldName, objType, autoValue, autoValOrigin=constants.DATA_SOURCE.DEST):
        """receives an organizations property name and the autogenerated
        value for that property, returns the equivalent autogenerated property
        that refers to the same object on the destination side

        :param autoFieldName: The field name that the 'autoValue' corresponds
            with.
        :type autoFieldName: str
        :param objType: The object type that the autoFieldName is a part of.
        :type objType: str
        :param autoValue: The actual value on of the field on the source side
            that needs to be translated.
        :type autoValue: str
        """
        self.loadData(objType, autoFieldName)
        #LOGGER.debug("data has been loaded")
        if autoValue in self.cacheStruct[autoFieldName][objType][autoValOrigin]:
            srcUserValue = self.cacheStruct[autoFieldName][objType][autoValOrigin][autoValue]
        elif autoValue in self.reverseStruct[autoFieldName][objType][constants.DATA_SOURCE.SRC]:
            srcUserValue = self.reverseStruct[autoFieldName][objType][constants.DATA_SOURCE.SRC][autoValue]
        else:
            msg = (
                "Cannot locate the corresponding value for the autogenerated " +
                f"{autoFieldName}: {autoValue} in either the source or the " +
                f"destination objects ({objType})"
            )
            LOGGER.error(msg)
            raise ValueError(msg)

        #LOGGER.debug(f'srcUserValue: {srcUserValue}')
        if srcUserValue not in self.cacheStruct[autoFieldName][objType][constants.DATA_SOURCE.DEST]:
            self.loadSingleDataSet(objType, constants.DATA_SOURCE.DEST, autoFieldName, srcUserValue)
        destAutoValue = self.cacheStruct[autoFieldName][objType][constants.DATA_SOURCE.DEST][srcUserValue]
        return destAutoValue

class CacheLoader:
    """This class glues the CKAN api to the cache, if sections of the cache have
    Not been populated then these methods will get called to populate various
    sections of the cache.  This should take place on an as needed basis.
    """
    def __init__(self):
        ckanParams = CKAN.CKANParams()
        destCKANWrap = ckanParams.getDestWrapper()
        srcCKANWrap = ckanParams.getSrcWrapper()

        self.wrapperMap = {
            constants.DATA_SOURCE.SRC: srcCKANWrap,
            constants.DATA_SOURCE.DEST: destCKANWrap
        }

        self.loadMethodMap = {
            constants.TRANSFORM_TYPE_ORGS: self.loadOrgs,
            constants.TRANSFORM_TYPE_USERS: self.loadUsers,
            constants.TRANSFORM_TYPE_GROUPS: self.loadGroups,
            constants.TRANSFORM_TYPE_PACKAGES: self.loadPackages,
            constants.TRANSFORM_TYPE_RESOURCES: self.loadResources
        }

        self.loadSingleRecordMethodMap = {
            constants.TRANSFORM_TYPE_ORGS: self.loadSingleOrg,
            constants.TRANSFORM_TYPE_USERS: self.loadSingleUser,
            constants.TRANSFORM_TYPE_GROUPS: self.loadSingleGroup,
            constants.TRANSFORM_TYPE_PACKAGES: self.loadSinglePackage,
            constants.TRANSFORM_TYPE_RESOURCES: self.loadSingleResource
        }

    def loadType(self, dataCacheObj, dataType, fieldName):
        """load the data for the specific data type

        :param cacheReference: [description]
        :type cacheReference: [type]
        :param dataType: [description]
        :type dataType: [type]
        """
        for dataOriginEnum in constants.DATA_SOURCE:
            # only load if the data hasn't already been loaded
            if not dataCacheObj.cacheStruct[fieldName][dataType][dataOriginEnum]:
                LOGGER.debug(f"loading data for field: {fieldName}, "
                             f"objtype: {dataType}, origin {dataOriginEnum}")
                rawData = self.loadMethodMap[dataType](dataOriginEnum)
                dataCacheObj.addRawData(rawData, dataType, dataOriginEnum)

    def loadSingleValue(self, dataCacheObj, dataType, dataOrigin, autoFieldName,
                        dataValue):
        """Looks up the data origin.

        If the origin is source then the data value needs is a autogenerated
        unique identifier, and the method needs to look up the user defined unique
        identifier that is aligned with the auto gen value.

        If the origin is a destination instance then the data value is a user
        defined unique identifier, and the method needs to look up the auto
        generated value.

        :param dataCacheObj: a reference to a DataCache object, the method attempts
            to update that object directly
        :type dataCacheObj: DataCache
        :param dataOrigin: Is the data associated with a source or destination
            CKAN instance.
        :type dataOrigin: constants.DATA_SOURCE
        :param autoFieldName: The name of the autogenerated field in the ckan instance
            that needs to be retrieved
            CKAN instance.
        :type autoFieldName: constants.DATA_SOURCE
        :param dataValue: see description above, if the dataOrigin is source then
            the autogenerated unique identifier value, otherwise the user
            generated unique identifier.
        :type dataValue: str
        """
        query = {constants.CKAN_SHOW_IDENTIFIER: dataValue}
        # below uses the data type to determine which single record load
        # method to call below.  That method gets sent the origin that allows
        # the single record load method to execute against the correct
        # ckan wrapper.
        singleRecord = self.loadSingleRecordMethodMap[dataType](dataOrigin, query)
        dataCacheObj.addRawDataSingleRecord(singleRecord, dataType, dataOrigin, autoFieldName, dataValue)

    def loadOrgs(self, dataOrigin):
        return self.wrapperMap[dataOrigin].getOrganizations(includeData=True)

    def loadSingleOrg(self, dataOrigin, query):
        return self.wrapperMap[dataOrigin].getOrganization(query)

    def loadUsers(self, dataOrigin):
        return self.wrapperMap[dataOrigin].getUsers(includeData=True)

    def loadSingleUser(self, dataOrigin, query):
        return self.wrapperMap[dataOrigin].getUser(query)

    def loadGroups(self, dataOrigin):
        return self.wrapperMap[dataOrigin].getGroups(includeData=True)

    def loadSingleGroup(self, dataOrigin, query):
        return self.wrapperMap[dataOrigin].getPackage(query)

    def loadPackages(self, dataOrigin):
        return self.wrapperMap[dataOrigin].getPackagesAndData(includeData=True)

    def loadSinglePackage(self, dataOrigin, query):
        return self.wrapperMap[dataOrigin].getPackage(query)

    def loadResources(self, dataOrigin):
        return self.wrapperMap[dataOrigin].getResources(includeData=True)

    def loadSingleResource(self, dataOrigin, query):
        return self.wrapperMap[dataOrigin].getResource(query)


class inValidDataType(ValueError):
    """Raised when the DataCacheFactory configuration encounters an unexpected
    value or type
    """

    def __init__(self, message):
        LOGGER.error(f"error message: {message}")
        self.message = message
