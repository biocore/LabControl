    // populate the table of potential plates to add
    var table = $('#searchPlateTable').DataTable(
        // NB: plate_type_list must be defined and filled OUTSIDE this snippet
        // of script.  An acceptable value for plate_type_list would be, e.g.,
        // ['gDNA', 'compressed gDNA'].
        // Likewise, get_only_quantified must be defined and filled OUTSIDE
        // this snippet. It is a boolean: true or false.
      {'ajax': {'url': '/plate_list', 'data': {'plate_type': JSON.stringify(plate_type_list), 'only_quantified': get_only_quantified}},
       'columnDefs': [{'targets': -1, // last column
                       'data': null,
                       'render': function(data, type, row, meta){
                            var plateId = data[0];
                            return "<button id='addBtnPlate" + plateId + "' class='btn btn-success btn-circle-small'><span class='glyphicon glyphicon-plus'></span></button>";
                       }
                      },
                      {'targets': -2, // second to last column
                       'data': null,
                       'render': function(data, type, row, meta){
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

    // Add function called by clicking on one of the buttons that adds a plate
    $('#searchPlateTable tbody').on('click', 'button', function() {
        var plateId = table.row( $(this).parents('tr') ).data()[0];
        try {
            addPlate(plateId);

            // Disable the button to add the plate to the list
            $('#addBtnPlate' + plateId).prop('disabled', true);
        } catch (e) {
            // Hide the modal to add plates
            $('#addPlateModal').modal('hide');
        }
    });