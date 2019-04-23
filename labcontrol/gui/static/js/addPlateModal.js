// NB: Any page importing this script MUST define a function
// addPlate that takes 1 parameter (the plate id) and does the work
// of actually collecting the necessary info from the plate the
// user has chosen to add.

// plateTypeList: a list of the types of plates to include in the add plate
// modal; an acceptable value for plateTypeList would be, e.g.,
// ['gDNA', 'compressed gDNA'].
// getOnlyQuantified: a boolean that is true if the only plates included in
// the add plate modal should be those that have already been quantified,
// false if all plates of the relevant types should be included.
function setUpAddPlateModal(plateTypeList, getOnlyQuantified) {
    // populate the table of potential plates to add
    var table = $('#searchPlateTable').DataTable({
            'ajax': {'url': '/plate_list',
                'data': {
                    'plate_type': JSON.stringify(plateTypeList),
                    'only_quantified': getOnlyQuantified
                }
            },
            'columnDefs': [
                {
                'targets': -1, // last column
                'data': null,
                'render': function (data, type, row, meta) {
                    var plateId = data[0];
                    return "<button id='addBtnPlate" + plateId + "' class='btn btn-success btn-circle-small'><span class='glyphicon glyphicon-plus'></span></button>";
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

    // Remove any existing event handler already attached to plate add buttons
    $('#searchPlateTable tbody').off('click', 'button');

    // Add function called by clicking on one of the buttons that adds a plate
    $('#searchPlateTable tbody').on('click', 'button', function () {
        var plateId = table.row($(this).parents('tr')).data()[0];
        try {
            addPlate(plateId);

            // Disable the button to add the plate to the list
            $('#addBtnPlate' + plateId).prop('disabled', true);
        } finally {
            // No matter what happens, hide the modal to add plates
            $('#addPlateModal').modal('hide');
        }
    });
}