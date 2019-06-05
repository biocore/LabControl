// NB: Any page importing this script MUST define a function
// addPlate that takes 1 parameter (the plate id) and does the work
// of actually collecting the necessary info from the plate the
// user has chosen to add for use by the specific page in question.

// Additionally, this script requires the following javascript libraries:
// jquery
// datatables

// This method creates the plate modal div that is filled and then
// shown/hidden by other methods in this library
function insertPlateModalDiv(elementIdToAppendTo = undefined,
                             addPlateModalId = "addPlateModal",
                             plateTableId = "searchPlateTable"){
    let div = $("<div class='modal fade' tabindex='-1' role='dialog' id='" +
        addPlateModalId + "'>\n" +
        "  <div class='modal-dialog modal-lg'>\n" +
        "    <div class='modal-content'>\n" +
        "      <div class='modal-header'>\n" +
        "        <button type='button' class='close' data-dismiss='modal' " +
        "aria-hidden='true'>&times;</button>\n" +
        "        <h3>Select plate(s) to add</h3>\n" +
        "      </div>\n" +
        "      <div class='modal-body'>\n" +
        "        <table id=\""+ plateTableId + "\" class=\"display\" " +
        "cellspacing=\"0\" width=\"100%\">\n" +
        "          <thead>\n" +
        "            <tr>\n" +
        "              <th>Plate id</th>\n" +
        "              <th>Plate name</th>\n" +
        "              <th>Creation timestamp</th>\n" +
        "              <th>Studies</th>\n" +
        "              <th>Add</th>\n" +
        "            </tr>\n" +
        "          </thead>\n" +
        "        </table>\n" +
        "      </div>\n" +
        "    </div>\n" +
        "  </div>\n" +
        "</div>");

    let selectorStr = "body";
    if (elementIdToAppendTo !== undefined){
        selectorStr = "#" + elementIdToAppendTo
    }

    div.appendTo($(selectorStr));
}

// This method makes a get call to retrieve a list of information (specified
// by the server-side handler, not here) about each
// plate with the specified type and quantification state.
// plateTypeList: a list of the types of plates to include results;
// an acceptable value for plateTypeList would be, e.g.,
// ['gDNA', 'compressed gDNA'].
// getOnlyQuantified: a boolean that is true if the only plates included in
// the results should be those that have already been quantified,
// false if all plates of the relevant types should be included.
function getPlateListPromise(plateTypeList, getOnlyQuantified) {
    // NB: This does NOT return a list of plate info--instead, it returns a
    // "promise" that will eventually provide the user access to a list of
    // plate info--AFTER the asynchronous ajax call is finished, whenever
    // that turns out to be.
    return $.ajax({
        url: '/plate_list',
        type: 'GET',
        data: {
            'plate_type': JSON.stringify(plateTypeList),
            'only_quantified': getOnlyQuantified
        }
    })
    .fail(function(xhr, ajaxOptions, thrownError){
        // Probably some more detailed error handling is called for, but
        // a little is better than none.
        alert("getPlateListPromise ajax call failed with error " +
        xhr.status + ": '" + thrownError + "'.");
    })
}

/*
* This method creates and populates a DataTables object with the input
* plateListInfo, and sets it as the contents of the dom object with the
* JQuery selector tableSelectorStr (which must already exist in the dom).
* tableSelectorStr is the string specifying the JQuery selector for the table
* to be populated, e.g. "#searchPlateTable".
*
* plateListInfo is a nested list of the format
* [
*   [21, "Test plate 1", "2019-05-09 21:21:15.386036",
*       ["Identification of the Microbiomes for Cannabis Soils"]
*   ],
*   [27, "Test plate 2", "2019-05-09 21:21:15.386036",
*       ["Identification of the Microbiomes for Cannabis Soils",
*       "Some Other Qiita Study"]
*   ]
*  ]
* ... where the outer list contains one entry for each plate, which in turn
* contains four entries: the plate id, the plate external id (e.g., name),
* the date the plate was created, and a list of the names of all the Qiita
* studies to which ANY of the samples on the plate belong.
* specificAddPlateBtnBaseId is the base part--that is, the part that doesn't
* actually include the plate id--of the the string id for the button one
* clicks to add a particular, specific plate; e.g., "addBtnPlate".
*/
function populatePlateTable(plateListInfo, tableSelectorStr,
                            specificAddPlateBtnBaseId) {
    // populate the table of potential plates to add
    return $(tableSelectorStr).DataTable({
            'data': plateListInfo,
            'columnDefs': [
                {
                    'targets': -1, // last column
                    'data': null,
                    'render': function (data, type, row, meta) {
                        var plateId = data[0];
                        return "<button id='" +
                            specificAddPlateBtnBaseId + plateId +
                            "' class='btn btn-success btn-circle-small'>" +
                            "<span class='glyphicon glyphicon-plus'></span>" +
                            "</button>";
                    }
                },
                {
                    'targets': -2, // second to last column
                    'data': null,
                    'render': function (data, type, row, meta) {
                        // index 3 in row is the list of studies
                        return data[3].join('<br/>');
                    }
                }
            ],
            // per https://datatables.net/reference/option/destroy:
            // Initialise a new DataTable as usual, but if there is an existing
            // DataTable which matches the selector, it will be destroyed and
            // replaced with the new table.
            'destroy': true,
            'order': [[0, "desc"]] // order rows in desc order by plate id
        }
    );
}

// This method generates a function that, when called, runs addPlate() for a
// specific plateId and appropriately enables/disables the add plate modal and
// buttons.  Closures are used to make that function parameterless.  The
// returned function is intended to be used as the onclick action of a button
// embedded in a row in a DataTables object, and won't act correctly if it
// is used elsewhere.
// dataTable is the actual DataTables.js object produced by a call to
// $(#<whatever the table id is>).DataTable().
// addPlateModalId is the string id of the div that represents the plate modal,
// e.g. "addPlateModal".
// specificAddPlateBtnBaseId is the base part--that is, the part that doesn't
// actually include the plate id--of the the string id for the button one
// clicks to add a particular, specific plate; e.g., "addBtnPlate".
function makeAddSpecificPlateButtonOnclick(dataTable, addPlateModalId,
                                           specificAddPlateBtnBaseId) {
    return function () {
        let plateId = dataTable.row($(this).parents('tr')).data()[0];
        let addPlateModalSelector = $("#" + addPlateModalId);
        let addPlateBtnSelector = $("#" + specificAddPlateBtnBaseId + plateId);

        // Hide the modal to add plates
        addPlateModalSelector.modal('hide');

        // Disable button to add this particular plate while we try to add it
        addPlateBtnSelector.prop('disabled', true);

        try {
            addPlate(plateId);
        } catch (e) {
            // if adding this plate *failed*, re-enable the add plate button
            // for this plate so the user can try again if they fix their
            // problem.
            addPlateBtnSelector.prop('disabled', false);
        }
    }
}

function setUpAddPlateModal(plateTypeList, getOnlyQuantified,
                            plateTableId = "searchPlateTable",
                            addPlateModalId = "addPlateModal",
                            specificAddPlateBtnBaseId = "addBtnPlate") {

    // NOTA BENE: ajax calls are asynchronous! (synchronous are deprecated)
    // This means we don't know when the result will come back and we can't do
    // ANYTHING that depends on this result--i.e., everything in this function
    // --until we know it is done.  Failure handling is not specific to this
    // function so it is specified in getPlateListPromise.
    getPlateListPromise(plateTypeList, getOnlyQuantified)
    .done(function (data) {
        //The data come back as in a dictionary object named data, which
        // contains just one entry--also with the key "data"
        let plateListInfo = (data["data"]);
        let tableSelectorStr = "#" + plateTableId;
        let table = populatePlateTable(tableSelectorStr, plateListInfo);

        let tbodySelector = $(tableSelectorStr + ' tbody');
        // Remove any existing event handler already attached to plate add btns
        tbodySelector.off('click', 'button');

        // Add function called by clicking on one of the btns that adds a plate
        let clickAddSpecificPlate = makeAddSpecificPlateButtonOnclick(table,
            addPlateModalId, specificAddPlateBtnBaseId);
        tbodySelector.on('click', 'button', clickAddSpecificPlate);
    });
}