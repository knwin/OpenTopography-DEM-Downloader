"""
Model exported as python and modfied codes for Selection DEM list, Extent coordinates, URL+parameters
Name : OpenTopography DEM Dwonloader
ver:1
Date: 2021 Dec 31
Group : DEM tools
With QGIS : 31612
version : 5

"""

from qgis.core import QgsProcessing, QgsSettings
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterExtent
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingException
from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils,QgsProcessingParameterRasterDestination
from qgis.PyQt.QtCore import QCoreApplication
import processing
from qgis.gui import QgsMessageBar


class Opentopodemdownloader(QgsProcessingAlgorithm):
    
    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'

    def initAlgorithm(self, config=None):
    
        my_settings = QgsSettings()
        my_api_key = my_settings.value("OpenTopographyDEMDownloader/ot_api_key", "")

        self.addParameter(QgsProcessingParameterEnum('DEMs', 'Select DEM to download', options=['SRTM 90m','SRTM 30m','ALOS World 3D 30m','SRTM GL1 Ellipsoidal 30m','Global Bathymetry SRTM15+ V2.1','Copernicus Global DSM 90m','Copernicus Global DSM 30m','NASADEM Global DEM'], allowMultiple=False, defaultValue=[0]))
        self.addParameter(QgsProcessingParameterExtent('Extent', 'Define extent to download', defaultValue=None))
        self.addParameter(QgsProcessingParameterString('layer_prefix', 'Prefix for layer name (i.e prefix_dem-name)', optional=True, multiLine=False, defaultValue=''))
        self.addParameter(QgsProcessingParameterString('API_key', 'Enter your API key', multiLine=False, defaultValue=my_api_key))
        #self.addParameter(QgsProcessingParameterBoolean('VERBOSE_LOG', 'logging', optional=True, defaultValue=False))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, self.tr('Output Raster')))

        
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)
        results = {}
        outputs = {}
        
        # process extent bbox information
        extent = parameters['Extent']
        epsg = extent.split(' ')[1]
        epsg = epsg[1:-1] # strip off [ ]
        print (epsg)
        extent = extent.split(' ')[0].split(',')
        south = extent[2]
        north = extent[3]
        west = extent[0]
        east = extent[1]
        if not(epsg=='EPSG:4326'):
            south_exp =  f'y(transform(make_point({west},{south}),\'{epsg}\',\'EPSG:4326\'))'
            west_exp =  f'x(transform(make_point({west},{south}),\'{epsg}\',\'EPSG:4326\'))'
            north_exp =  f'y(transform(make_point({east},{north}),\'{epsg}\',\'EPSG:4326\'))'
            east_exp =  f'x(transform(make_point({east},{north}),\'{epsg}\',\'EPSG:4326\'))'
            context_exp = QgsExpressionContext()
            #context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(vl))
            south = QgsExpression(south_exp).evaluate(context_exp)
            west = QgsExpression(west_exp).evaluate(context_exp)
            north = QgsExpression(north_exp).evaluate(context_exp)
            east = QgsExpression(east_exp).evaluate(context_exp)
            
        
        print (south,west,north,east)
        '''
        dems = {
            'SRTMGL1 (SRTM 30m)' : 'SRTMGL1',
            'SRTMGL3 (SRTM 90m)' : 'SRTMGL3',
            'AW3D30 (ALOS World 3D 30m)' : 'AW3D30',
            'SRTMGL1_E (SRTM GL1 Ellipsoidal 30m)' : 'SRTMGL1_E',
            'SRTM15Plus (Global Bathymetry SRTM15+ V2.1)' : 'SRTM15Plus',
            'COP90 (Copernicus Global DSM 90m)*' : 'COP90',
            'COP30 (Copernicus Global DSM 30m)*':'COP30',
            'NASADEM (NASADEM Global DEM)*': 'NASADEM'}
            '''
        dem_codes = ['SRTMGL3','SRTMGL1','AW3D30','SRTMGL1_E','SRTM15Plus','COP90','COP30','NASADEM']
        dem_names = ['_SRTM90m','_SRTM30m','_AW3D30','_SRTM30m_E','_SRTM15Plus','_COP90','_COP30','_NASADEM']
        dem_code = dem_codes[parameters['DEMs']]
        dem_name = parameters['layer_prefix'] + dem_names [parameters['DEMs']]
        dem_url = f'https://portal.opentopography.org/API/globaldem?demtype={dem_code}&south={south}&north={north}&west={west}&east={east}&outputFormat=GTiff'
        dem_url=dem_url + "&API_Key=" + parameters['API_key']
        print (dem_url)
        dem_file = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        print (dem_file)
        try:
            # Download file
            alg_params = {
                'URL': dem_url,
                'OUTPUT': dem_file
            }            
            outputs['DownloadFile'] = processing.run('native:filedownloader', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            my_settings.setValue("OpenTopographyDEMDownloader/ot_api_key", parameters['API_key'])
            
        except:
            raise QgsProcessingException ("API Key Error: Please check your API key OR Cannot Access DEM")
       

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}  
        # Load layer into project           
        
        if dem_file == 'TEMPORARY_OUTPUT':
            alg_params = {           
                'INPUT': outputs['DownloadFile']['OUTPUT'],
                'NAME': dem_name
            }
        else:
            alg_params = {           
                'INPUT': dem_file,
                'NAME': dem_name
            }
        
        outputs['LoadLayerIntoProject'] = processing.run('native:loadlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        #return results
        return {self.OUTPUT:outputs['DownloadFile']['OUTPUT']}
        
    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)
    
    def shortHelpString(self):
        help_text = """
        ????????????????????????????????? OpenTopography (https://opentopography.org/) ?????? DEM ??????????????????????????????????????????????????????????????? ??????????????????????????? ??????????????????????????????????????? ????????????????????????????????? ???????????????????????????????????????????????????????????????????????????????????? 
        
        DEM ???????????? ???????????????????????? ??????????????? API key ?????????????????????????????????????????????????????????????????? API key ??????????????????????????? https://opentopography.org/blog/introducing-api-keys-access-opentopography-global-datasets ????????????????????????????????????
        
        ???????????????????????? -??????????????????????????????????????????
        ?????????????????? - ???????????????-???????????????????????????-??????????????????????????????
             - ?????????????????????????????????????????? ???????????? ?????????????????? ???????????????????????????????????????????????????????????????????????? ??????????????? (????????????????????????????????????)
        
        This tool will download DEM for the extent defined by user, from OpenTopography (https://opentopography.org/)
        You need API key to download DEMs (since Jan 2022). 
        Read https://opentopography.org/blog/introducing-api-keys-access-opentopography-global-datasets how to get API key.
        
        Developed by: Kyaw Naing Win
        Date: 28 Nov 2021 
        email: kyawnaingwinknw@gmail.com
        
        change log:
        ver05 - 2 Feb 2022
         - API key is stored and retrieved if exists
         
        ver04 - 27 Jan 2022
         - Script can be used in model builder
         
        ver03 - 21 Jan 2022
         - ALL DEM needs API key
        
        ver01 - 29 Nov 2021..
         - accept any CRS when defining extent
        
        ver00 - 28 Nov 2021
         - first working version
         - none EPSG:4326 extent will throw error

        """
        return self.tr(help_text)

    def name(self):
        return 'OpenTopoDEMDownloader'

    def displayName(self):
        return 'OpenTopograhy DEM downloader'

    def group(self):
        return 'DEM tools'

    def groupId(self):
        return 'DEM tools'

    def createInstance(self):
        return Opentopodemdownloader()
