/**
 *
 * Changes the current plate name
 *
 **/
function change_plate_name() {
  $('#updateNameBtn').prop('disabled', true).find('span').addClass('glyphicon glyphicon-refresh gly-spin');
  $('#newNameInput').prop('disabled', true);
  var value = $('#newNameInput').val().trim();
  $('#plateName').html(value);
  $('#updatePlateName').modal('hide');
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
  // TODO: Check if it can be removed (i.e. samples of this study have not been plated)
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
  var $opt = $('#plate-conf-select option:selected');
  // TODO: Check if we are modifying a plate that already exists
  var plateId = undefined;
  var pv = new PlateViewer('plate-map-div', plateId, $opt.attr('pm-data-rows'), $opt.attr('pm-data-cols'));
}
