/**
 *
 * Changes the current plate name
 *
 **/
function change_plate_name() {
  $('#updateNameBtn').prop('disabled', true).find('span').addClass('glyphicon glyphicon-refresh gly-spin');
  $('#newNameInput').prop('disabled', true);
  var value = $('#newNameInput').val().trim();
  var plateId = $('#plateName').prop('pm-data-plate-id');
  if (plateId !== undefined) {
    // Modifying a plate that already exists, ask the server to change the
    // plate configuration
    $.ajax({url: '/plate/' + plateId + '/',
           type: 'PATCH',
           data: {'op': 'replace', 'path': '/name', 'value': value},
           success: function (data) {
             $('#plateName').html(value);
             $('#updatePlateName').modal('hide');
          },
          error: function (jqXHR, textStatus, errorThrown) {
            bootstrapAlert(jqXHR.responseText, 'danger');
            $('#updatePlateName').modal('hide');
          }
    });
  } else {
    $('#plateName').html(value);
    $('#updatePlateName').modal('hide');
  }
  // This is only needed when the modal was open for first time automatically when
  // creating a new plate. However, it doesn't hurt having it here executed always
  $('#updatePlateNameCloseBtn').prop('hidden', false);
  $('#updatePlateName').data('bs.modal').options.keyboard = true;
  $('#updatePlateName').data('bs.modal').options.backdrop = true;
  // Remove the cancel button from the modal
  $('#cancelUpdateNameBtn').remove();
};

/**
 *
 * Adds a study to the plating procedure
 *
 * @param {integer} studyId Id of the study to add
 *
 **/
function add_study(studyId) {
  $.get('/study/' + studyId + '/', function (data) {
    // Create the element containing the study information and add it to the list
    var $aElem = $("<a href='#' onclick='activate_study(" + studyId + ")'>");
    $aElem.addClass('list-group-item').addClass('study-list-item');
    $aElem.attr('id', 'study-' + studyId);
    $aElem.attr('pm-data-study-id', studyId);
    $aElem.append('<label><h4>' + data.study_title + '</h4></label>');
    $aElem.append(' Total Samples: ' + data.total_samples);
    var $buttonElem = $("<button class='btn btn-danger btn-circle pull-right' onclick='remove_study(" + studyId + ");'>");
    $buttonElem.append("<span class='glyphicon glyphicon-remove'></span>")
    $aElem.append($buttonElem);

    $('#study-list').append($aElem);

    if($('#study-list').children().length === 1) {
        activate_study(studyId);
    }

    // Disable the button to add the study to the list
    $('#addBtnStudy' + studyId).prop('disabled', true);

    // Hide the modal to add studies
    $('#addStudyModal').modal('hide');
  })
    .fail(function (jqXHR, textStatus, errorThrown) {
      bootstrapAlert(jqXHR.responseText, 'danger');
      $('#addStudyModal').modal('hide');
    });
};

/**
 *
 * Removes a study from the plating procedure
 *
 * @param {integer} studyId Id of the study to remove
 *
 **/
function remove_study(studyId) {
  // Remove the study from the list:
  $('#study-' + studyId).remove();
  // Re-enable the button to add the study to the list
  $('#addBtnStudy' + studyId).prop('disabled', false);
}

function activate_study(studyId) {
  var $elem = $('#study-' + studyId);
  if ($elem.hasClass('active')) {
    // If the current element already has the active class, remove it,
    // so no study is active
    $elem.removeClass('active');
  } else {
    // Otherwise choose the curernt study as the active
    $elem.parent().find('a').removeClass('active');
    $elem.addClass('active');
  }
}

/**
 *
 * Changes the configuration of a plate
 *
 **/
function change_plate_configuration() {
  var pv, $opt;
  $opt = $('#plate-conf-select option:selected');
  var plateId = $('#plateName').prop('pm-data-plate-id');
  if (plateId !== undefined) {
    throw "Can't change the plate configuration of an existing plate"
  } else {
    // reset the container before updating the grid configuration
    $('#plate-map-div').empty().height(0);
    pv = new PlateViewer('plate-map-div', undefined, undefined, $opt.attr('pm-data-rows'), $opt.attr('pm-data-cols'));
    // Enable the plate create button now that a plate config is selected
    $('#createPlateBtn').prop('disabled', false);
  }
}

function createPlate(){
      var plateName = $('#newNameInput').val().trim();
      var plateConf = $('#plate-conf-select option:selected').val();
      $.post('/process/sample_plating', {'plate_name': plateName, 'plate_configuration': plateConf}, function (data) {
        var plateId = data['plate_id'];
        var processId = data['process_id'];

        $('#plateName').prop('pm-data-plate-id', plateId);
        $('#plateName').prop('pm-data-process-id', processId);
        // Once the plate has been created, we can disable the plate config select
        $('#plate-conf-select').prop('disabled', true);

        // reset the container before updating the grid configuration
        $('#plate-map-div').empty().height(0);
        var $opt = $('#plate-conf-select option:selected');
        var pv = new PlateViewer('plate-map-div', undefined, undefined, $opt.attr('pm-data-rows'), $opt.attr('pm-data-cols'));
        pv.plateId = plateId;
        pv.processId = processId;
        // we can only instantiate the notes box when we have a process id
        pv.notes = new NotesBox(pv.container.parent(),
                                  '/process/sample_plating/notes',
                                  processId);

        // Disable the plate create button
        $('#createPlateBtn').prop('disabled', true);

        // Show the plate details div
        $('#plateDetails').prop('hidden', false);
      });
}
