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
function change_plate_configuration(parent) {
  var pv, $opt, opt_id;
  $opt_id = parent.find('#plate-conf-select').attr('selected_opt');
  $opt = parent.find('#plate-conf-select').find(opt_id);
  var plateId = parent.find('#plateName').attr('pm-data-plate-id');
  if (plateId !== undefined) {
    throw "Can't change the plate configuration of an existing plate"
  } else {
    pv = new PlateViewer('plate-map-div', undefined, undefined, $opt.attr('pm-data-rows'), $opt.attr('pm-data-cols'));
  }
}

/**
 *
 * Add html per plate
 *
 **/
 function add_plate_html(plateId){

   html = $("<div id=plate-"+plateId+"></div>");
   html.append($("<label></label>").append("<h3>Plate '<span id='plateName' class='plateName-"+plateId+"'>New Plate</span>'</h3>"));
   // Add buttons next to the plate name
   html.append("<button class='btn btn-default' data-toggle='modal'"+
   " data-target='#updatePlateName'>"+
   "<span class='glyphicon glyphicon-edit'></span> Change name</button>")
       .append("<a class='btn btn-success' href='/'>Save</a>");

   // Plate configuration div
   // Add the select and options to div
   formGroup = $("<div class='form-group'></div>");
   formGroup.append("<label class='control-label'><h4>Plate configuration:</h4></label>");
   select = $("  <select id='plate-conf-select' class='form-control plate-conf-select'></select>");
   select.append("<option selected>Choose plate configuration...</option>");
   $.get('/plate/' + plateId + '/plateConfigSelect', function(data) {
     data['plate_confs'].forEach(function(element){
       var id = element[0];
       var name  = element[1];
       var rows = element[2];
       var cols = element[3];
       select.append("<option value='"+id+"' pm-data-rows='"+rows+"' pm-data-cols='"+cols+"'>"+name+"</option>");
     });
   });
   formGroup.append(select);
   html.append(formGroup);

   div = $("<div></div>");
   div.append($("<label></label>").append("<h4>Studies being plated</h4>"));
   div.append("<button class='btn btn-success' data-toggle='modal' data-target='#addStudyModal'><span class='glyphicon glyphicon-plus'></span> Add study</button>");
   div.append("<div id='study-list'></div>");
   html.append(div);

   // Plate map div
   html.append("<h4>Plate Map</h4>");
   html.append("<div id='plate-map-div' style='width:100%;height:250px'></div>");

   html.append("<h4>Well comments</h4>");
   html.append("<div id='well-plate-comments' class='comment-box'></div>");

   $('#work_area').append(html);
 }

/**
 *
 * Create layout per plateViewer
 *
 **/
function add_plate_html_functions(processId, plateId){
  var parent = $('#plate-'+plateId);
  // Set the focus on the text input when the modal to change the plate name
  // is shown. Also reset any other change that we may have done to the
  // modal
  parent.find('#updatePlateName').on('shown.bs.modal', function () {
    parent.find('#newNameInput').focus().prop('disabled', false).val('');
    parent.find('#updateNameBtn').prop('disabled', true).find('span').removeClass('glyphicon glyphicon-refresh gly-spin');
    parent.find('#newNameDiv').removeClass('has-success').addClass('has-error').find('span').removeClass('glyphicon-ok').addClass('glyphicon-remove');
    var pId = parent.find('#plateName').prop('pm-data-plate-id');
    if (pId !== undefined) {
      // The user is modifying an existing plate - do not force the user
      // to introduce a plate name to close the modal
      parent.find('#updatePlateNameCloseBtn').prop('hidden', false);
      parent.find('#updatePlateName').data('bs.modal').options.keyboard = true;
      parent.find('#updatePlateName').data('bs.modal').options.backdrop = true;
      // Remove the cancel button from the modal
      parent.find('#cancelUpdateNameBtn').remove();
    }
  });
    // Set the validation on the plate name
  parent.find('#newNameInput').keyup(function(e) {
    onKeyUpPlateName(e, 'newNameInput', function() {
      parent.find('#updateNameBtn').prop('disabled', parent.find('#newNameDiv').hasClass('has-error'));
    }, change_plate_name);
  });


  // Set the study search table
  var table = parent.find('#searchStudyTable').DataTable(
    {'ajax': '/study_list',
     'columnDefs': [{'targets': -1,
                     'data': null,
                     'render': function(data, type, row, meta) {
                        var studyId = data[0];
                        return "<button id='addBtnStudy" + studyId + "' class='btn btn-success btn-circle-small'><span class='glyphicon glyphicon-plus'></span></button>";
                      }}]
    });
  // Add the function to the buttons that add the study to the plate
  parent.find('#searchStudyTable tbody').on('click', 'button', function() {
    add_study(table.row( $(this).parents('tr') ).data()[0]);
  });

  if (plateId === undefined) {

    // The user is creating a new plate. Force the user to introduce a new
    // plate name
    parent.find('#updatePlateName').modal('show');
  } else {
    // Set the plateId in a prop so we can recover it whenever we want
    parent.find('.plateName-'+plateId).attr('pm-data-plate-id', plateId);
    // Disable the plate config select
    parent.find('#plate-conf-select').attr('disabled', true);
    // Update the plate name in the interface
    $.get('/plate/' + plateId + '/', function(data) {
      parent.find('#plateName').html(data['plate_name']);
      parent.find('#plate-conf-select').val(data['plate_configuration'][0]);
      parent.find('#plate-conf-select').attr('selected_opt',data['plate_configuration'][0]);
    });
    // Load the plate map
    var pv = new PlateViewer('plate-map-div', plateId, processId);

  }

  // Add the change callback to the plate configuration select
  parent.find('#plate-conf-select').on('change', change_plate_configuration(parent));
}
