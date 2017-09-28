/**
 *
 * @class PlateViewer
 *
 * Shows the plate information
 *
 * @param {string} target The name of the target container for the plate viewer
 * @param {int} plateId OPTIONAL The id of the plate to visualize
 * @param {int} rows OPTIONAL If plateId is not provided, the number of rows
 * @param {int} cols OPTIONAL If plateId is not provided, the number of columns
 *
 * @return {PlateViewer}
 * @constructs PlateViewer
 *
 **/
function PlateViewer(target, plateId, rows, cols) {
  this.target = $('#' + target);
  this.plateId = null;

  if (!plateId) {
    if (!rows || !cols) {
      // This error should never show up in production
      bootstrapAlert('PlateViewer developer error: rows and cols should be provided if plateId is not provided');
    } else {
      this.initialize(rows, cols);
    }
  } else {
    // Ignore rows and cols and use the plateId to retrieve the plate
    // information and initialize the object
    this.plateId = plateId;
  }
};

/**
 *
 * Initializes SlickGrid to show the plate layout
 *
 * @param {int} rows The number of rows
 * @param {int} cols The number of columns
 *
 **/
PlateViewer.prototype.initialize = function (rows, cols) {
  this.rows = rows;
  this.cols = cols;
  this.data = [];

  var sgOptions = {editable: true,
                   enableCellNavigation: true,
                   asyncEditorLoading: false,
                   enableColumnReorder: false,
                   autoEdit: true};
  var sgCols = [{id: 'selector', name: '', field: 'header', width: 30}]
  for (var i = 0; i < this.cols; i++) {
    sgCols.push({id: i, name: i+1, field: i, editor: SampleCellEditor});
  }
  var rowId = 'A';
  for (var i = 0; i < this.rows; i++) {
    var d = (this.data[i] = {});
    d["header"] = rowId;
    rowId = getNextRowId(rowId);
  }

  this.grid = new Slick.Grid(this.target, this.data, sgCols, sgOptions);
};

/**
 *
 * @class SampleCellEditor
 *
 * This class represents a Sample cell editor defined by the SlickGrid project
 *
 * This is heavily based on SlickGrid's TextEditor
 * (https://github.com/6pac/SlickGrid/blob/master/slick.editors.js)
 * And the SlickGrid's example of autocomplete:
 * (https://github.com/6pac/SlickGrid/blob/master/examples/example-autocomplete-editor.html)
 *
 * @param {Object} args Arguments passed by SlickGrid
 *
 **/
function SampleCellEditor(args) {
  var $input;
  var defaultValue;
  var scope = this;

  // Do not use the up and down arrow to navigate the cells so they can be used
  // to choose the sample from the autocomplete dropdown menu
  this.keyCaptureList = [Slick.keyCode.UP, Slick.keyCode.DOWN];

  this.init = function () {
    $input = $("<input type='text' class='editor-text' />")
        .appendTo(args.container)
        .on("keydown.nav", function (e) {
          if (e.keyCode === $.ui.keyCode.LEFT || e.keyCode === $.ui.keyCode.RIGHT) {
            e.stopImmediatePropagation();
          }
        })
        .focus()
        .select();

    $input.autocomplete({source: autocomplete_search_samples});
  };

  this.destroy = function () {
    $input.remove();
  };

  this.focus = function () {
    $input.focus();
  };

  this.getValue = function () {
    return $input.val();
  };

  this.setValue = function (val) {
    $input.val(val);
  };

  this.loadValue = function (item) {
    defaultValue = item[args.column.field] || "";
    $input.val(defaultValue);
    $input[0].defaultValue = defaultValue;
    $input.select();
  };

  this.serializeValue = function () {
    return $input.val();
  };

  this.applyValue = function (item, state) {
    item[args.column.field] = state;
  };

  this.isValueChanged = function () {
    return (!($input.val() == "" && defaultValue == null)) && ($input.val() != defaultValue);
  };

  this.validate = function () {
    if (args.column.validator) {
      var validationResults = args.column.validator($input.val());
      if (!validationResults.valid) {
        return validationResults;
      }
    }

    return {
      valid: true,
      msg: null
    };
  };

  this.init();
};

/**
 *
 * Function to fill up the autocomplete dropdown menu for the samples
 *
 * @param {object} request Request object sent by JQuery UI autocomple
 * @param {function} response Callback function sent by JQuery UI autocomplete
 *
 **/
function autocomplete_search_samples(request, response) {
  // Check if there is any study chosen
  var $studies = $('.study-list-item.active');
  var studyIds = [];
  if ($studies.length === 0) {
    // There are no studies chosen - search over all studies in the list:
    $.each($('.study-list-item'), function (index, value) {
      studyIds.push($(value).attr('pm-data-study-id'));
    });
  } else {
    $.each($studies, function (index, value) {
      studyIds.push($(value).attr('pm-data-study-id'));
    });
  }

  // Perform all the requests to the server
  var requests = [];
  $.each(studyIds, function (index, value) {
    requests.push($.get('/study/' + value + '/sample_search?term=' + request.term));
  });

  $.when.apply($, requests).then(function () {
    // The nature of arguments change based on the number of requests performed
    // If only one request was performed, then arguments only contain the output
    // of that request. On the other hand, if there was more than one request,
    // then arguments is a list of results
    var arg = (requests.length === 1) ? [arguments] : arguments;
    var results = [];
    $.each(arg, function(index, value) {
      results = results.concat($.parseJSON(value[0]));
    });
    response(results);
  });
}
