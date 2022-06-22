#####################################################################################################
# PARETO was produced under the DOE Produced Water Application for Beneficial Reuse Environmental
# Impact and Treatment Optimization (PARETO), and is copyright (c) 2021 by the software owners: The
# Regents of the University of California, through Lawrence Berkeley National Laboratory, et al. All
# rights reserved.
#
# NOTICE. This Software was developed under funding from the U.S. Department of Energy and the
# U.S. Government consequently retains certain rights. As such, the U.S. Government has been granted
# for itself and others acting on its behalf a paid-up, nonexclusive, irrevocable, worldwide license
# in the Software to reproduce, distribute copies to the public, prepare derivative works, and perform
# publicly and display publicly, and to permit other to do so.
#####################################################################################################
"""
Module to read in input data from Excel spreadsheets and convert it into the
format that Pyomo requires

Authors: PARETO Team (Andres J. Calderon, Markus G. Drouven)
"""

import pandas as pd
import requests
import numpy as np


def _read_data(_fname, _set_list, _parameter_list):
    """
    This methods uses Pandas methods to read from an Excel spreadsheet and output a data frame
    Two data frames are created, one that contains all the Sets: _df_sets, and another one that
    contains all the parameters in raw format: _df_parameters
    """
    _df_parameters = {}
    _temp_df_parameters = {}
    _data_column = ["value"]
    proprietary_data = False
    _df_sets = pd.read_excel(
        _fname,
        sheet_name=_set_list,
        header=0,
        index_col=None,
        usecols="A",
        squeeze=True,
        dtype="string",
        keep_default_na=False,
    )

    # Cleaning Sets. Checking for empty entries, and entries with the keyword: PROPRIETARY DATA
    for df in _df_sets:
        for idx, i in enumerate(_df_sets[df]):
            if i.lower() == "proprietary data":
                _df_sets[df][idx] = ""
        _df_sets[df].replace("", np.nan, inplace=True)
        _df_sets[df].dropna(inplace=True)

    _df_parameters = pd.read_excel(
        _fname,
        sheet_name=_parameter_list,
        header=1,
        index_col=None,
        usecols=None,
        squeeze=True,
        keep_default_na=False,
    )
    # A parameter can be defined in column format or table format.
    # Detect if columns which will be used to reshape the dataframe by defining
    # what columns are Sets or generic words
    # If _set_list is empty, it is assummed that a parameter is column format is being read.
    # and _set_list is created based on the DataFrame column names, except for the last name,
    # which is used as the data column name.
    if len(_set_list) == 0:
        for i in _df_parameters:
            _set_list.extend(list(_df_parameters[i].columns)[:-1])
            _data_column.append(list(_df_parameters[i].columns)[-1])

    _set_list = list(set(_set_list))
    _data_column = list(set(_data_column))
    generic_words = ["index", "nodes", "time", "pads", "quantity"]
    remove_columns = ["unnamed", "proprietary data"]
    keyword_strings = ["PROPRIETARY DATA", "proprietary data", "Proprietary Data"]
    for i in _df_parameters:
        if proprietary_data is False:
            proprietary_data = any(
                x in _df_parameters[i].values.astype(str) for x in keyword_strings
            )
            if proprietary_data is False:
                proprietary_data = any(
                    x in _df_parameters[i].columns for x in keyword_strings
                )
        # Checking for tabs, new lines and entries with the keyword "PROPRIETARY DATA" and replacing them for an empty string
        _df_parameters[i].replace(
            to_replace=keyword_strings,
            value="",
            inplace=True,
        )
        _df_parameters[i].replace(
            to_replace=[r"\\t|\\n|\\r", "\t|\n|\r"], value="", regex=True, inplace=True
        )
        # Removing whitespaces
        _df_parameters[i] = _df_parameters[i].applymap(
            lambda x: x.strip() if isinstance(x, str) else x
        )
        # Removing all the columns that contain only empty strings
        # _df_parameters[i] = _df_parameters[i][_df_parameters[i].columns[~_df_parameters[i].eq('').all(0)]]
        # Removing columns that are unnamed or have the keyword "proprietary data" as column name
        drop_col = [
            i
            for i in _df_parameters[i].columns
            if any(x in str(i).lower() for x in remove_columns)
        ]
        _df_parameters[i].drop(columns=drop_col, inplace=True)
        # Removing all the rows that contain only empty strings
        _df_parameters[i] = _df_parameters[i][~_df_parameters[i].eq("").all(1)]

        index_col = []
        for j in _df_parameters[i].columns:
            # If a column name is in the set_list or in the list of keywords, it is assumed the column is an index and saved in index_col
            if str(j).split(".")[0].lower() in [s.lower() for s in _set_list] or any(
                x in str(j).lower() for x in generic_words
            ):
                index_col.append(j)

        # If the number of index_col is equal to the total columns of the dataframe
        # it means that this is a parameter in column format. Therefore, the indices are defined for all
        # the columns of the dataframe except for the last column which contains the data
        if len(index_col) != 0 and (len(index_col) == len(_df_parameters[i].columns)):
            data_column = index_col.pop()

        if len(index_col) != 0:
            _df_parameters[i].set_index(index_col, inplace=True)

    # Creating a DataFrame that contains a boolean for proprietary_data. This is used as a "flag" in
    # generate_report() to output warnings if the report contains proprietary data.
    _df_parameters["proprietary_data"] = pd.DataFrame(
        [proprietary_data], columns=["Value"]
    )

    return [_df_sets, _df_parameters, _data_column]


def _cleanup_data(_df_parameters):
    """
    This method does two things:
    1) It replaces empty strings cells with a Numpy nan
    2) It formats the headers and column names as strings
    """
    for i in _df_parameters:
        _df_parameters[i].replace("", np.nan, inplace=True)
        _df_parameters[i].columns = _df_parameters[i].columns.astype(str)

    return _df_parameters


def _df_to_param(data_frame, data_column):
    """
    This module converts the data frame that contains Parameters into the adequate
    format that Pyomo expects for paramerters:
    Input_parameter = {(column_index, row_header): value}
    """
    _df_parameters = {}
    _temp_df_parameters = {}
    for i in data_frame:

        # If the data frame is empty, that is, no input data was provided in the Excel
        # file then an empty parameter is created:
        if data_frame[i].empty:
            _df_parameters[i] = data_frame[i].to_dict()
        # If the data frame has one column named "value", it means the dataframe corresponds to
        # a parameter in column format. In this case, the dataframe is converted directly
        # to a dictionary and the column name is used as the key of said dictionary
        elif str(data_frame[i].columns[0]).split(".")[0].lower() in [
            i.lower() for i in data_column
        ]:
            data_column_key = data_frame[i].columns[0]
            _temp_df_parameters[i] = data_frame[i].to_dict()
            _df_parameters[i] = _temp_df_parameters[i][data_column_key]

        else:
            _df_parameters[i] = data_frame[i].stack().to_dict()

    return _df_parameters


def get_data(fname, set_list, parameter_list):
    """
    This method uses Pandas methods to read data for Sets and Parameters from excel spreadsheets.
    - Sets are assumed to not have neither a header nor an index column. In addition, the data
      should be placed in column A, row 2
    - Parameters can be in either table or column format. Table format: Requires a header
      (usually time periods) and an index column whose elements should be contained in a Set.
      The header should start in row 2, and the index column should start in cell A3.
      Column format: Does not require a header. Each set should be placed in one column,
      starting from column A and row 3. Data should be provided in the last column.

    Outputs:
    The method returns one dictionary that contains a list for each set, and one dictionary that
    contains parameters in format {‘param1’:{(set1, set2): value}, ‘param1’:{(set1, set2): value}}

    To use this method:

    set_list = [list of tabs that contain sets]
    parameter_list = [list of tabs that contain parameters]
    [df_sets, df_parameters] = get_data(fname='path\\to\\excel\\file\\INPUT_DATA.xlsx',
                                        set_list, parameter_list)

        ###############################################################################
                                     SET DEFINITION
        ###############################################################################
        model.p = Set(initialize=_df_sets['ProductionPads'].values,
                        doc='Production Pads')
        model.c = Set(initialize=_df_sets['CompletionsPads'].values,
                        doc='Completions Pads')
        model.d = Set(initialize=_df_sets['SWDSites'].values,
                        doc='SWD Sites')
        model.t = Set(initialize=_df_sets['TimePeriods'].values,
                        doc='planning weeks')
        model.l = Set(initialize=model.p | model.c | model.d,
                        doc='Superset that contains all locations')

        ###############################################################################
        #                           PARAMETER DEFINITION
        ###############################################################################
        model.drive_times = Param(model.l, model.l,
                                    initialize=df_parameters['DriveTimes'],
                                    doc="Driving times between locations")
        model.completion_demand = Param(model.c, model.t,
                                        initialize=df_parameters['CompletionsDemand'],
                                        doc="Water demand for completion operations")
        model.flowback_rates = Param(model.c, model.t,
                                        initialize=df_parameters['FlowbackRates'],
                                     doc="Water flowback rate")

    It is worth highlighting that the Set for time periods "model.s_T" is derived by the
    method based on the Parameter: CompletionsDemand which is indexed by T

    Similarly, the Set for Water Quality Index "model.s_W" is derived by the method based
    on the Parameter: PadWaterQuality which is indexed by W
    """
    # Reading raw data, two data frames are output, one for Sets, and another one for Parameters
    [_df_sets, _df_parameters, data_column] = _read_data(
        fname, set_list, parameter_list
    )

    # Parameters are cleaned up, e.g. blank cells are replaced by NaN
    _df_parameters = _cleanup_data(_df_parameters)

    # The set for time periods is defined based on the columns of the parameter for
    # Completions Demand. This is done so the user does not have to add an extra tab
    # in the spreadsheet for the time period set
    if "CompletionsDemand" in parameter_list:
        _df_sets["TimePeriods"] = _df_parameters[
            "CompletionsDemand"
        ].columns.to_series()

    # The set for water quality components (e.g. TDS, Cl) is defined based on the columns of the parameter for
    # PadWaterQuality. This is done so the user does not have to add an extra tab
    # in the spreadsheet for the water quality component set
    if "PadWaterQuality" in parameter_list:
        _df_sets["WaterQualityComponents"] = _df_parameters[
            "PadWaterQuality"
        ].columns.to_series()

    # The data frame for Parameters is preprocessed to match the format required by Pyomo
    _df_parameters = _df_to_param(_df_parameters, data_column)

    return [_df_sets, _df_parameters]


def set_consistency_check(param, *args):
    """
    Purpose:    This method checks if the elements included in a table or parameter have been defined as part of the
                Sets that index such parameter.

    How to use: The method requires one specified parameter (e.g. ProductionRates) AND one OR several sets over which
                the aforementioned parameter is declared (e.g.ProductionPads, ProductionTanks, TimePeriods). In general,
                the method can be run as follows: set_consistency_check(Parameter, set_1, set_2, etc)

    Output:     set_consistency_check() raises a TypeError exception If there are entries in the Parameter that are not
                contained in the Sets, and prints out a list with all the entries that require revision
    """
    # Getting a net list of all the elements that are part of the parameter
    raw_param_elements = list([*param.keys()])
    temp_param_elements = []
    i = []
    for i in raw_param_elements:
        # The if condition checks if the parameter has only one index or more. If it is a tuple, it means the
        # parameter has 2 indices or more, and the second loop is required. If it is not a tuple,
        # then the second loop is skipped to avoid looping through the characters of the element i,
        # which would cause a wrong warning
        if type(i) == tuple:
            for j in i:
                temp_param_elements.append(j)
        else:
            temp_param_elements.append(i)
    net_param_elements = set(temp_param_elements)

    # Getting a net list of all the elements that are part of the Sets that index the parameter
    temp_sets_elements = []
    for i in args:
        for j in i:
            temp_sets_elements.append(j)
    net_sets_elements = set(temp_sets_elements)

    net_elements = net_param_elements - net_sets_elements

    # If net_elements contains elements, it means the parameter constains elements that have not
    # been defined as part of its Sets, therefore, an exception is raised
    if net_elements:
        raise TypeError(
            f"The following elements have not been declared as part of a Set: {sorted(net_elements)}"
        )
    else:
        return 0


def od_matrix(inputs):

    """
    This method allows the user to request drive distances and drive times using Bing maps API and
    Open Street Maps API.
    The method accept the following input arguments:
    - origin:   REQUIRED. Data containing information regarding location name, and coordinates
                latitude and longitude. Two formats are acceptable:
                {(origin1,"latitude"): value1, (origin1,"longitude"): value2} or
                {origin1:{"latitude":value1, "longitude":value2}}
                The first format allows the user to include a tab with the corresponding data
                in a table format as part of the workbook casestudy.

    - destination:  OPTIONAL. If no data for destination is provided, it is assumed that the
                    origins are also destinations.

    - api:  OPTIONAL. Specify the type of API service, two options are supported:
                Bing maps: https://docs.microsoft.com/en-us/bingmaps/rest-services/
                Open Street Maps: https://www.openstreetmap.org/
                If no API is selected, Open Street Maps is used by default

    - api_key:  An API key should be provided in order to use Bing maps. The key can be obtained at:
                https://www.microsoft.com/en-us/maps/create-a-bing-maps-key

    - output:   OPTIONAL. Define the paramters that the method will output. The user can select:
                'time': A list containing the drive times between the locations is returned
                'distance': A list containing the drive distances between the locations is returned
                'time_distance': Two lists containing the drive times and drive distances betweent
                the locations is returned
                If not output is specified, 'time_distance' is the default

    - fpath:    OPTIONAL. od_matrix() will ALWAYS output an Excel workbook with two tabs, one that
                contains drive times, and another that contains drive distances. If not path is
                specified, the excel file is saved with the name 'od_output.xlsx' in the current
                directory.

    - create_report OPTIONAL. if True an Excel report with drive distances and drive times is created
    """
    # Information for origing should be provided
    if "origin" not in inputs.keys():
        raise Exception("The input dictionary must contain the key *origin*")
    else:
        origin = inputs["origin"]

    inputs_default = {
        "destination": None,
        "api": None,
        "api_key": None,
        "output": None,
        "fpath": None,
        "create_report": True,
    }

    for i in inputs_default.keys():
        if i not in list(inputs.keys()):
            inputs[i] = inputs_default[i]

    destination = inputs["destination"]
    api = inputs["api"]
    api_key = inputs["api_key"]
    output = inputs["output"]
    fpath = inputs["fpath"]
    create_report = inputs["create_report"]

    # Check that a valid API service has been selected and make sure an api_key was provided
    if api in ("open_street_map", None):
        api_url_base = "https://router.project-osrm.org/table/v1/driving/"

    elif api == "bing_maps":
        api_url_base = "https://dev.virtualearth.net/REST/v1/Routes/DistanceMatrix?"
        if api_key is None:
            raise Warning("Please provide a valid api_key")
    else:
        raise Warning("{0} API service is not supported".format(api))

    # If no destinations were provided, it is assumed that the origins are also destinations
    if destination is None:
        destination = origin

    origins_loc = []
    destination_loc = []
    origins_dict = {}
    destination_dict = {}

    # =======================================================================
    #                          PREPARING DATA FORMAT
    # =======================================================================
    # Check if the input data has a Pyomo format:
    #   origin={(origin1,"latitude"): value1, (origin1,"longitude"): value2}
    # if it does, the input is modified to a Dict format:
    #   origin={origin1:{"latitude":value1, "longitude":value2}}
    if isinstance(list(origin.keys())[0], tuple):
        for i in list(origin.keys()):
            origins_loc.append(i[0])
        origins_loc = list(sorted(set(origins_loc)))

        for i in origins_loc:
            origins_dict[i] = {
                "latitude": origin[i, "latitude"],
                "longitude": origin[i, "longitude"],
            }
        origin = origins_dict

    if isinstance(list(destination.keys())[0], tuple):
        for i in list(destination.keys()):
            destination_loc.append(i[0])
        destination_loc = list(sorted(set(destination_loc)))

        for i in destination_loc:
            destination_dict[i] = {
                "latitude": destination[i, "latitude"],
                "longitude": destination[i, "longitude"],
            }
        destination = destination_dict

    # =======================================================================
    #                           SELECTING API
    # =======================================================================

    if api in (None, "open_street_map"):
        # This API works with GET requests. The general format is:
        # https://router.project-osrm.org/table/v1/driving/Lat1,Long1;Lat2,Long2?sources=index1;index2&destinations=index1;index2&annotations=[duration|distance|duration,distance]
        coordinates = ""
        origin_index = ""
        destination_index = ""
        # Building strings for coordinates, source indices, and destination indices
        for index, location in enumerate(origin.keys()):
            coordinates += (
                str(origin[location]["longitude"])
                + ","
                + str(origin[location]["latitude"])
                + ";"
            )
            origin_index += str(index) + ";"

        for index, location in enumerate(destination.keys()):
            coordinates += (
                str(destination[location]["longitude"])
                + ","
                + str(destination[location]["latitude"])
                + ";"
            )
            destination_index += str(index + len(origin)) + ";"

        # Dropping the last character ";" of each string so the API get request is valid
        coordinates = coordinates[:-1]
        origin_index = origin_index[:-1]
        destination_index = destination_index[:-1]
        response = requests.get(
            api_url_base
            + coordinates
            + "?sources="
            + origin_index
            + "&destinations="
            + destination_index
            + "&annotations=duration,distance"
        )
        response_json = response.json()

        df_times = pd.DataFrame(
            index=list(origin.keys()), columns=list(destination.keys())
        )
        df_distance = pd.DataFrame(
            index=list(origin.keys()), columns=list(destination.keys())
        )
        output_times = {}
        output_distance = {}

        # Loop for reading the output JSON file
        if response_json["code"].lower() == "ok":
            for index_i, o_name in enumerate(origin):
                for index_j, d_name in enumerate(destination):

                    output_times[(o_name, d_name)] = (
                        response_json["durations"][index_i][index_j] / 3600
                    )
                    output_distance[(o_name, d_name)] = (
                        response_json["distances"][index_i][index_j] / 1000
                    ) * 0.621371

                    df_times.loc[o_name, d_name] = output_times[(o_name, d_name)]
                    df_distance.loc[o_name, d_name] = output_distance[(o_name, d_name)]
        else:
            raise Warning("Error when requesting data, make sure your API key is valid")

    elif api == "bing_maps":
        # Formating origin and destination dicts for Bing Maps POST request, that is, converting this structure:
        # origin={origin1:{"latitude":value1, "longitude":value2},
        #           origin2:{"latitude":value3, "longitude":value4}}
        # destination={destination1:{"latitude":value5, "longitude":value6,
        #               destination2:{"latitude":value7, "longitude":value8}}
        # Into the following structure:
        # data={"origins":[{"latitude":value1, "longitude":value2},
        #                   {"latitude":value3, "longitude":value4}],
        #       "destinations":[{"latitude":value5, "longitude":value6},
        #                       {"latitude":value7, "longitude":value8}]}

        origins_post = []
        destinations_post = []
        for i in origin.keys():
            origins_post.append(
                {"latitude": origin[i]["latitude"], "longitude": origin[i]["longitude"]}
            )

        for i in destination.keys():
            destinations_post.append(
                {"latitude": origin[i]["latitude"], "longitude": origin[i]["longitude"]}
            )

        # Building the dictionary with the adequate structure compatible with Bing Maps
        data = {
            "origins": origins_post,
            "destinations": destinations_post,
            "travelMode": "driving",
        }

        # Sending a POST request to the API
        header = {"Content-Type": "application/json"}
        response = requests.post(
            api_url_base + "key=" + api_key, headers=header, json=data
        )
        response_json = response.json()

        # Definition of two empty dataframes that will contain drive times and distances.
        # These dataframes wiil be exported to an Excel workbook
        df_times = pd.DataFrame(
            index=list(origin.keys()), columns=list(destination.keys())
        )
        df_distance = pd.DataFrame(
            index=list(origin.keys()), columns=list(destination.keys())
        )
        output_times = {}
        output_distance = {}

        # Loop for reading the output JSON file
        if response_json["statusDescription"].lower() == "ok":
            for i in range(
                len(response_json["resourceSets"][0]["resources"][0]["results"])
            ):
                data_temp = response_json["resourceSets"][0]["resources"][0]["results"][
                    i
                ]
                origin_index = data_temp["originIndex"]
                destination_index = data_temp["destinationIndex"]

                o_name = list(origin.keys())[origin_index]
                d_name = list(destination.keys())[destination_index]
                output_times[(o_name, d_name)] = data_temp["travelDuration"] / 60
                output_distance[(o_name, d_name)] = (
                    data_temp["travelDistance"] * 0.621371
                )

                df_times.loc[o_name, d_name] = output_times[(o_name, d_name)]
                df_distance.loc[o_name, d_name] = output_distance[(o_name, d_name)]
        else:
            raise Warning("Error when requesting data, make sure your API key is valid")

    # Define the default name of the Excel workbook
    if fpath is None:
        fpath = "od_output.xlsx"

    if create_report is True:
        # Dataframes df_times and df_distance are output as sheets in an Excel workbook whose directory
        # and name are defined by variable 'fpath'
        with pd.ExcelWriter(fpath) as writer:
            df_times.to_excel(writer, sheet_name="DriveTimes")
            df_distance.to_excel(writer, sheet_name="DriveDistances")

    # Identify what type of data is returned by the method
    if output in ("time", None):
        return_output = output_times
    elif output == "distance":
        return_output = output_distance
    elif output == "time_distance":
        return_output = [output_times, output_distance]
    else:
        raise Warning(
            "Provide a valid type of output, valid options are:\
                        time, distance, time_distance"
        )

    return return_output
