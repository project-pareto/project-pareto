========================
How to Use the PARETO UI
========================

.. _how-to-use-ui-page:

Step-by-step guide
------------------

.. container::

   .. container::

      .. container::

         **Step 1.** Download the latest version of PARETO for your
         operating system at the `Project PARETO Website <https://www.project-pareto.org/software>`_.

         .. container:: screenshot-div

            |software-website|

         **Step 2.** Follow the installation steps to install the
         application. For Windows, see below:

         .. container:: screenshot-div

            |windows-installer|

         **Step 3.** Run the application. You should see a splash page
         before being redirected to the scenarios page:

         .. container:: screenshot-div
            
            |scenarios-page|

         **Step 4.** Click on "Create new scenario". Download from one
         of the available sample inputs, or use your own data, then name the scenario and click
         "Create scenario":

         .. container:: screenshot-div

            |create-scenario|

         **Step 5.** Browse the input plots and tables, with the option
         to edit any of the inputs:

         .. container:: screenshot-div

            |input-page|

         **Step 6.** Click "CONTINUE TO OPTIMIZATION" button, and choose
         from the optimization settings:

         .. container:: screenshot-div

            |model-settings|

         **Step 7.** Click "OPTIMIZE" to run the PARETO strategic model:

         .. container:: screenshot-div

            |running-model|

         **Step 8.** When the model is finished running, the KPI
         dashboard will be visible from the model results section:

         .. container:: screenshot-div

            |kpi-dashboard.|

         **Step 9.** Analyze the output by looking through tables and
         graphs, including the Sankey diagram that interactively
         displays the transport of produced water (via piping or trucking):

         .. container:: screenshot-div

            |sankey-diagram|

         **Step 10.** If you are unhappy with any of PARETO's
         infrastructure decisions, feel free to override with your own
         decisions in the "infrastructure buildout" tab:

         .. container:: screenshot-div

            |infrastructure-override|

         **Step 11.** Compare different scenarios by clicking on any of
         the compare icons from the scenario page:

         .. container:: screenshot-div

            |scenario-comparison|


.. _map_example:

Map Feature (Beta)
------------------

.. container::

   *Note: This section describes a pre-release feature with limited functionality at this time.*

   Users can upload a map file to the UI that represents their network. 
   By using this feature, users can greatly reduce the amount of input data required to begin working with PARETO.
   
   The UI can handle Keyhole Markup Language (KML) and zipped KML (KMZ) as map inputs. KML is an XML-based language schema for expressing web-based maps. KML files can be created using Google Earth, Google Maps, or ESRI ArcGIS, or using a plain text editor. More information about KML/KMZ can be found `here <https://developers.google.com/kml/documentation/kml_tut>`_.

   :download:`Download A Sample Map File Here <assets/Sample_Map_Scenario.kml>`

   .. container::

      **Step 1.** Navigate to the PARETO UI scenario list page. Click create scenario and upload your map file. You will be directed to this input page:

      .. container:: screenshot-div

         |map-input|

      **Step 2.** Download the auto-generated Excel input file, fill in the required data, and re-upload to continue with optimizing your scenario. Or, 
      fill the data in directly through the UI:

      .. container:: screenshot-div

         |edit-input-map|

         Once the scenario is ready to go, you can continue optimizing and interacting with the UI by following the steps above. 

.. |software-website| image:: ./img/software-website.png
   :class: screenshot
.. |windows-installer| image:: ./img/windows-installer.png
   :class: screenshot
.. |scenarios-page| image:: ./img/scenarios-page.png
   :class: screenshot
.. |create-scenario| image:: ./img/create-scenario.png
   :class: screenshot
.. |input-page| image:: ./img/input-page.png
   :class: screenshot
.. |model-settings| image:: ./img/model-settings.png
   :class: screenshot
.. |running-model| image:: ./img/running-model.png
   :class: screenshot
.. |kpi-dashboard.| image:: ./img/kpi-dashboard.png
   :class: screenshot
.. |sankey-diagram| image:: ./img/sankey-diagram.png
   :class: screenshot
.. |infrastructure-override| image:: ./img/infrastructure-override.png
   :class: screenshot
.. |scenario-comparison| image:: ./img/scenario-comparison.png
   :class: screenshot
.. |map-input| image:: ./img/map-input.png
   :class: screenshot
.. |full-map| image:: ./img/full-map.png
   :class: screenshot
.. |edit-input-map| image:: ./img/edit-input-map.png
   :class: screenshot
