This tutorial will walk you through the Labman process from plating your samples to preparing your sequencing runs.

Home Screen
=========

* Labman- Returns you to the home page
* Plates

	* List- Brings you to a list of all of the plates on Labman
		* You can highlight plates here to continue processing them
	* Search- Bring you to search boxes to find plates based on their plate comments or well comments or both
	* Plate samples- Creates a table accounting for which samples are in which well
	* Extract gDNA- Extracts your gDNA from your samples
	* Compress gDNA plates- Compresses gDNA samples from a 96 well plate to a 384 well plate

		* Up to 4 plates can be compressed
	* Normalize gDNA plates- Normalizes shotgun sequencing input 
	* Prepare amplicon sequencing- Prepares 16S to be run
	* Prepare shotgun libraries- Prepares shotgun sequences to be run
	* PicoGreen Quantification- Quantifies DNA concentrations in sample and library plates 

* Pools

	* List- Brings you to a list of all of the pools on Labman
		* You can highlight pools here to continue processing them
	* Pool library plates- Combines samples together for multiplexing 
	* Prepare amplicon sequencing pool- Combines pools together

* Sequencing runs

	* List- Brings you to a list of all of the sequencing runs on Labman 
		* You can highlight sequencing runs here to continue processing them
	* Prepare sequencing run- Creates a sequencing file for the sequencer 
	
* Studies

	* List- Brings you to list of all of the public studies on Qiita


16S 
===


Plating
---------


Plate Samples
^^^^^^^^^^^^^

To create a new plate, go to “Plates” drop-down menu on the top of the screen and select “Plate Samples.” This will take you to a new page that will gather information to create your plate.

Importantly, information about studies (and their associated samples) must be added prior to this plating process. This ensures that all samples in a plate are accounted for and correctly linked to metadata for downstream analysis.

You will be brought to a new screen where you will be asked to enter a “Plate name”. These names have no restrictions.

Once your plate name is created, you will be asked to fill in information regarding the “Plate configuration” used in your experiment. 

Below “Plate configuration” you will be asked to choose the “Studies being plated.” After choosing “Add Study”, a list of studies available in the database will appear. On this page, select the green plus sign to add a study to your plate. If you want to add an additional study, simply select “Add Study” again and repeat the steps—this will allow you to combine samples from multiple studies onto a single plate.

After choosing a “Plate configuration,” a table will be created that matches your plate type. Here you can insert your sample names. Each well will autofill from your study, or studies, selected and will show 20 options at a time. These wells are case sensitive. Be sure to type the study ID in front of your sample name. 

If your samples are not found within your metadata from your Qiita study, you will receive an error. If your sample names are long and you are unable to read them, you can resize the columns by dragging the edges. 

If you input 2 identical sample names on the same plate, both wells will become red. 

If you input a sample that is already on another plate within your study, you will be alerted with a message in your “Well comments” text box at the bottom of your screen.

If you want to add a comment to a well, right click the well after you have added a sample name. Once you select “Add comment,” an “Add comment to well” window will pop-up where you can input a note. The edges of your sample name will now be highlighted green and your comment will appear in the “Well comments” text box. To remove or edit your comment, right click the well. Select the “Add comment” again to make your edits in the pop-up window. 

When you are finished plating your samples, select “Save” and you will be returned to the home screen.


Extract gDNA
^^^^^^^^^^^^

When you are ready to extract your gDNA, go to the “Plates” drop-down menu and select “Extract gDNA.”

This will bring you to the “gDNA plate extraction” page. Here, you can choose the plate from which you would like to extract by selecting “Add plate.” This will bring up a menu of all of the plates samples. Use the green plus sign to select your plate. 

This will bring up a text box asking for information on materials used for your extraction. Importantly, these materials must exist (or be created) in the database, ensuring that the values recorded are consisten across samples.Here you will be asked to select your “gDNA plate name” (if you had more than one plate in your study), your “KingFisher robot” used, your “EpMotion robot”, your “EpMotion tool”, and finally the “Extraction kit” used. The first four options require values to already exist in the database, and therefore only have drop-down menus. The extraction kit option allows for free text. However, if the inputted extraction kit does not exist, you will be prompted to add them to the system.

You will then be asked for the “Elution volume (µL)” and the “Extraction date”. The date can be past or present, however you cannot select a future date.

When you are finished with your plate extraction, select “Extract” and you will be returned to the home screen.

If you would like to look at your extraction again, return to the “Extract gDNA” page and select your plate. You will return to the same interface, displaying the recorded values. However, you won’t be able to change any of the inputted information. To change the information, you must re-extract your plate. If you would like to re-extract a plate, you must restart at the “Plate Samples” step and give your plate a different name. 


Prepare Amplicon Libraries
^^^^^^^^^^^^^^^^^^^^^^^^

When you are ready to prepare your amplicon libraries, go to the “Plates” drop-down menu and select “Prepare Amplicon Libraries.”

This brings you to the “Amplicon library prep” page. Here, you will choose the plates for which you are preparing amplicon libraries by selecting “Add plate.” This will bring up a dialogue of all gDNA extraction plates. You can select your sample plates by selecting the adjacent green plus sign.

This will bring up input fields asking for information on your amplicon libraries. Here you will be asked to select your “Library plate name” (if you had more than one plate in your study), your “Primer plate” used, your “EpMotion robot”, your “EpMotion TM300 8 tool”, your “EpMotion TM50 8 tool”, your “Master mix”, and finally the “Water lot” used. As with gDNA extraction, the first five options deal with equipment that must already exist in the database, and therefore only have drop-down menus.he master mix and water lot options allow for free text; if the inputs do not exist, you will be prompted to add them to the system.

You will then be asked for the “PCR Total Volume (µL)” and the “Preparation date”. The date can be past or present, however you cannot select a future date.

When you are finished with preparing your amplicon libraries, select “Prepare libraries” and you will be returned to the home screen.


PicoGreen Quantification
^^^^^^^^^^^^^^^^^^^^^^

After PCR, the amplified libraries are quantified with PicoGreen to assess success and facilitate sample pooling. When you are ready to quantify your plates with PicoGreen, go to the “Plates” drop-down menu and select “PicoGreen Quantification”.

This brings you to the “Quantify plates” page. Here, you will choose the plate you are quantifying by selecting “Add plate.” This will bring up a menu of all of the prepared amplicon libraries. You can select your samples by selecting the green plus sign next to your samples.

This will bring up a text box asking for information on your quantification. Here you will be asked to upload your “Plate reader output” file. 

When you are finished with your quantification with PicoGreen, select “Submit” and you will be brought to a page to review your quantification values. Here, all of your quantification values will be matched with their corresponding wells. If these are correct, select “Confirm”. If they are not correct, select cancel to be brought back to the quantification page to fix the errors.


Pooling
----------


Pool Library Plates
^^^^^^^^^^^^^^^^^

When you are ready to pool your library plates, go to the “Pools” drop-down menu and select “Pool library plates”.

This brings you to the “Pool library plates” page. Here, you will choose your plate type—in this case, “Amplicon”. This will then bring up another line where you can add your plates to be pooled. To add your plates to be pooled, select “Add plate.” This will bring up a menu of all of the quantified plates. You can select your samples by clicking on the green plus sign next to your plates.

This will bring up a text box asking for information on your quantified plates. Here you will be asked to select your “Total amount of DNA (ng)”, your “Minimum concentration value (ng/µL”, your “Maximum concentration value (ng/µL)”, your “Blanks value (ng/µL)”, your “EpMotion robot”, and your “EpMotion destination tube”. The EpMotion robot asks for specific information and therefore only has a drop-down menu, while the rest of the options allow for free text.

When you are finished, select “Compute pooling values.” You will receive a .csv file to be uploaded to your liquid handling robot to pool the actual samples. . Then you will be returned to the home screen.

CANT MOVE ON FROM HERE TO KNOW IF GO BACK TO HOME SCREEN


Prepare Amplicon Sequencing Pool
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Typically, samples from multiple pooled library plates are combined into a single run. When you are ready to comine your library plate pools, go to the “Pools” drop-down menu and select “Pool amplicon sequencing pool”.

This brings you to the “Prepare sequencing pool” page. Here, you will name your pool and choose the plate pools. To add your plate pools, select “Add pool.” This will bring up a menu of all of the pools. You can select your pool by clicking on the green plus sign next to your pool.

Here you can gather information on the total amount of “Pooled samples”, “Percentage”, “DNA concentration (ng/µL)”, “ 5µg Amt (ng)”, and “Sample Amt (µL)”.

CANT MOVE ON FROM HERE


Sequencing Runs
---------------------

Prepare Sequencing Run
^^^^^^^^^^^^^^^^^^^^^

When you are ready to prepare your sequencing run, go to the “Sequencing runs” drop-down menu and select “Prepare sequencing run”. This interface will generate a sample sheet with the appropriate values for Illumina sequencing.

Here, you will name your run and run experiment, select your “Sequencer”, add “sequencing pools” by selecting “Add pool” and selecting your pool by clicking on the green plus sign next to your pool, adding the number of “Forward cycles” and “Reverse cycles”, adding your “Principal Investigator”, and finally adding any “additional contacts” by selecting the “Add contact” button and selecting your contact by clicking on the green plus sign next to their email.

When you are finished with preparing your sequencing run, select “Create”. A message will appear at the top of the page alerting your that your information is now stored. Your study is now updated so that you can't modify the values, and a download button should appear to download the sample sheet for sequencing.

Sample sheets can always be re-downloaded by searching for a particular run on the “List sequencing runs” option under the “Sequencing runs” drop-down on the main menu.

Shotgun
======

Plating
---------


Plate Samples
^^^^^^^^^^^^^

To create a new plate, go to the “Plates” drop-down menu on the top of the screen and select “Plate Samples.” This will take you to a new page that will gather information to create your plate.


You will be brought to a new screen where you will be asked to enter a “Plate name”. These names have no restrictions.

Once your plate name is created, you will be asked to fill in information regarding the “Plate configuration” used in your experiment. 

Below “Plate configuration” you will be asked to choose the “Studies being plated.” After choosing “Add Study”, a list of Qiita studies will appear. On this page, select the green plus sign to add a study to your plate. If you want to add an additional study, simply select “Add Study” again and repeat the steps.

After choosing a “Plate configuration,” a table will be created that matches your plate type. Here you can insert your sample names. These wells are case sensitive. Be sure to type your Qiita ID in front of your sample name. Each well will autofill from your study, or studies, selected and will show 20 options at a time. 

If your samples are not found within your metadata from your Qiita study, you will receive an error. If your sample names are long and you are unable to read them, you can resize the columns by dragging the edges. 

If you input 2 identical samples on the same plate, both wells will become red. 

If you input a sample that is already on another plate within your study, you will be alerted with a message in your “Well comments” text box at the bottom of your screen.

If you want to add a comment to a well, right click the well after you have added a sample name. Once you select “Add comment,” an “Add comment to well” window will pop-up where you can input a note. The edges of your sample name will now be highlighted green and your comment will appear in the “Well comments” text box. To remove or edit your comment, right click the well. Select the “Add comment” again to make your edits in the pop-up window. 


When you are finished plating your samples, select “Save” and you will be returned to the home screen.


Extract gDNA
^^^^^^^^^^^^

When you are ready to extract your gDNA, go to the “Plates” drop-down menu and select “Extract gDNA.”

This will bring you to the “gDNA plate extraction” page. Here, you can choose the plate you would like to extract from, by selecting “Add plate.” This will bring up a menu of all of the plates samples where you can use the green plus sign to select your plate. 

This will bring up a text box asking for information on your extraction. Here you will be asked to select your “gDNA plate name” (if you had more than one plate in your study), your “KingFisher robot” used, your “EpMotion robot”, your “EpMotion tool”, and finally the “Extraction kit” used. The first four options ask for specific information and therefore only have drop-down menus, while the extraction kit option allows for free text. However, if the inputted extraction kit does not exist, you will be prompted to add them to the system.

You will then be asked for the “Elution volume (µL)” and the “Extraction date”. The date can be past or present, however you cannot select a future date.

When you are finished with your plate extraction, select “Extract” and you will be returned to the home screen.

If you would like to look at your extraction again, return to the “Extract gDNA” page and select your plate. However, you won’t be able to change any of the inputted information. To change the information, you must re-extract your plate. If you would like to re-extract a plate, you must restart at the “Plate Samples” step and give your plate a different name. 


Compress gDNA plates
^^^^^^^^^^^^^^^^^^^^

While gDNA is extracted in 96-well plate format, shotgun libraries are prepared in a 384-well format, compressing up to 4 separate 96-well extraction plates into a single gDNA plate. When you are ready to compress your gDNA, go to the “Plates” drop-down menu and select “Compress gDNA plates”.

This will bring you to the “gDNA plate compression” page. Here, you can choose the plate you would like to compress, by selecting “Add plate.” This will bring up a menu of all available extracted gDNA plates Use the green plus sign to select your plate. You can compress up to four 96-well plates at a time. Samples from constituent 96-well plates will be spread evenly across the compressed 384-well plate in the following pattern:

A B A B...
C D C D...
A B A B...
C D C D...

You will then be asked to name your combined plate under “Compressed plate name”.

When you are finished with compressing your gDNA plate, select “Compress” and you will be returned to the home screen.


PicoGreen Quantification
^^^^^^^^^^^^^^^^^^^^^^

When you are ready to quantify your compressed gDNA plates with PicoGreen, go to the “Plates” drop-down menu and select “PicoGreen Quantification”.

This brings you to the “Quantify plates” page. Here, you will choose the plate you are quantifying by selecting “Add plate.” This will bring up a menu of all of the prepared amplicon libraries. You can select your samples by selecting the green plus sign next to your samples.

This will bring up a text box asking for information on your quantification. Here you will be asked to upload your “Plate reader output” file. 

When you are finished with your quantification with PicoGreen, select “Submit” and you will be brought to a page to review your quantification values. Here, all of your quantification values will be matched with their corresponding wells. If these are correct, select “Confirm”. If they are not correct, select cancel to be brought back to the quantification page to fix the errors.


Normalize gDNA Plates
^^^^^^^^^^^^^^^^^^^^^

Normalized amounts of DNA are added to shotgun sequencing libraries from compressed gDNA plates. When you are ready to normalize your quantified, compressed gDNA plates, go to the “Plates” drop-down menu and select “Normalize gDNA plates”.

This will bring you to the “Normalization” page. Here, you can choose the plate you would like to normalize, by selecting “Add plate.” This will bring up a menu of all of the plates samples where you can use the green plus sign to select your plate. Be sure to use the new plate that you created in the “Compress gDNA plates” step.

You will then be asked to select your “Water lot”, name your plate, input your “Total Volume”, input your total “ng”, what your “Min volume” and “Max volume” are, what your “Resolution” is, and if you want to “Reformat”. Most of the options allow for free text. However, if the inputted “water lot” does not exist, you will be prompted to add it to the system. 


Prepare Shotgun Libraries
^^^^^^^^^^^^^^^^^^^^^^^^

When you are ready to prepare your shotgun libraries, go to the “Plates” drop-down menu and select “Prepare shotgun libraries.”

This brings you to the “Shotgun library prep” page. Here, you will choose the normalized, compressed gDNA plate for which you are preparing libraries by selecting “Add plate.” This will bring up a menu of all available normalized gDNA platess. You can select your samples by selecting the green plus sign next to your samples. Be sure to use the new plate that you created in the “Normalize gDNA plates” step.

This will bring up a text box asking for information on your shotgun libraries. Here you will be asked to select index primers by separately selecting your “i5 plate” and your “i7 plate”. As with equipment like robots, primer plates are expected to be added infrequently, and must already exist in the database.

You will then be asked to name your plate, input your “kappa hyper plus kit”, input your “Stub lot” and input your “Volume (mL)”. Though all of the options are free text, if the “kappa hyper plus kit” and “Stub lot” do not exist, you will be prompted to add them to the system.

When you are finished with preparing your shotgun libraries, select “Prepare libraries” and you will be returned to the home screen.


PicoGreen Quantification
^^^^^^^^^^^^^^^^^^^^^^

Prepared, amplified shotgun libraries are quantified with PicoGreen prior to pooling and sequencing. When you are ready to quantify your plates with PicoGreen, go to the “Plates” drop-down menu and select “PicoGreen Quantification”. This process is otherwise identical to the gDNA plate quantification.

This brings you to the “Quantify plates” page. Here, you will choose the plate you are quantifying by selecting “Add plate.” This will bring up a menu of all of the prepared amplicon libraries. You can select your samples by selecting the green plus sign next to your samples.

This will bring up a text box asking for information on your quantification. Here you will be asked to upload your “Plate reader output” file. 

When you are finished with your quantification with PicoGreen, select “Submit” and you will be brought to a page to review your quantification values. Here, all of your quantification values will be matched with their corresponding wells. If these are correct, select “Confirm”. If they are not correct, select cancel to be brought back to the quantification page to fix the errors.


Pooling
----------


Pool Library Plates
^^^^^^^^^^^^^^^^^

When you are ready to pool your shotgun library plates, go to the “Pools” drop-down menu and select “Pool library plates”.

This brings you to the “Pool library plates” page. Here, you will choose the library plate type—in this case, shotgun. This will then bring up another line where you can add your plates to be pooled. To add your plates to be pooled, select “Add plate.” This will bring up a menu of all of the quantified shotgun plates. You can choose your samples by selecting the green plus sign next to your samples. Be sure to use the new plate that you created in the “Prepare shotgun libraries” step.

NOT SURE IF THIS IS CORRECT (BELOW) CAN’T CONTINUE PAST HERE

Several algorithms are available for pooling. Select your desired pooling algorithm from the drop-down menu. This will bring up a text box asking for information on your quantified plates. Here, we will use “Minimum Volume” pooling. Enter your desired “Total library quantity  (nmol)”, your “Minimum concnetration (nM)”, your “Floor pooling volume (nL)”, and your “Average library size”.
When you are finished pooling your library plates, select “Compute pooling values.” Verify that the pooled quantities appear correct, and then select “Pool.” A button will appear with the label “Download pool file”, which will allow you to download the Echo-formatted pick list to provide to the robot to physically pool your libaries. 


Sequencing Runs
---------------------


Prepare Sequencing Run
^^^^^^^^^^^^^^^^^^^^^

When you are ready to prepare your sequencing run, go to the “Sequencing runs” drop-down menu and select “Prepare sequencing run”. This interface will generate a sample sheet with the appropriate values for Illumina sequencing.

Here, you will name your run and run experiment, select your “Sequencer”, add “sequencing pools” by selecting “Add pool” and selecting your pool by clicking on the green plus sign next to your pool, adding the number of “Forward cycles” and “Reverse cycles”, adding your “Principal Investigator”, and finally adding any “additional contacts” by selecting the “Add contact” button and selecting your contact by clicking on the green plus sign next to their email.

When you are finished with preparing your sequencing run, select “Create”. A message will appear at the top of the page alerting your that your information is now stored. Your study is now updated so that you can't modify the values, and a download button should appear to download the sample sheet for sequencing.

Sample sheets can always be re-downloaded by searching for a particular run on the “List sequencing runs” option under the “Sequencing runs” drop-down on the main menu.

