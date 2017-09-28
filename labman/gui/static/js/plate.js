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
 * Adds a study to the plate
 *
 * @param {integer} studyId Id of the study to add
 *
 **/
function add_study(studyId) {
  $.get('/study/' + studyId + '/', function (data) {
    var $aElem = $("<a href='#' class='list-group-item' id='study-" + studyId + "'>");
    $aElem.append('<label><h4>' + data.study_title + '</h4></label>');
    $aElem.append(' Total Samples: ' + data.total_samples);
    var $buttonElem = $("<button class='btn btn-danger btn-circle pull-right' onclick='$(\"#study-" + studyId + "\").remove();'>");
    $buttonElem.append("<span class='glyphicon glyphicon-remove'></span>")
    $aElem.append($buttonElem);
    $('#study-list').append($aElem);
    $('#addStudyModal').modal('hide');
  })
    .fail(function (jqXHR, textStatus, errorThrown) {
      bootstrapAlert(jqXHR.responseText, 'danger');
      $('#addStudyModal').modal('hide');
    });
};

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
