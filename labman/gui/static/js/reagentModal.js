// This component is a modal to add new reagents to the system

Vue.component('reagent-modal', {
  // reagent-type: The reagent type
  // id-prefix: Prefix to set up the id for all internal modal values
  // input-taget; The input element that the user is typing the reagent
  // checks-callback: Function to execute when the input-target changes
  props: ['reagent-type', 'id-prefix', 'input-target', 'checks-callback'],
  methods: {
    /**
     *
     * Function to provide the autocomplete options for the input-target
     *
     * @param request Object Request object, contains a single element "term"
     * @param response Function Callback to provide the list of options
     *
     * This function performs an AJAX query to get the list of reagent lots
     * that contain the term that the user typed in
     *
     **/
    autocompleteSearchReagent: function(request, response) {
      $.get('/composition/reagent?reagent_type=' + this.reagentType + '&term=' + request.term, function (data) {
        response($.parseJSON(data));
      })
        .fail(function (jqXHR, textStatus, errorThrown) {
          bootstrapAlert(jqXHR.responseText, 'danger');
          // The autocomplete documentation specifies that you should always
          // call response, even when a failure happens, to make sure that the
          // object is left in a safe state.
          response([]);
        });
    },

    /**
     *
     * Function to execute when the input-target changes value
     *
     * This function performs an AJAX call to check if the user provided reagent
     * already exists. If it doesn't exist, it shows the modal to create it.
     *
     **/
    onChangeAutocomplete: function () {
      // Check if the given reagent exists - if it doesn't exist, show the modal
      // to create it
      let that = this;
      var value = $('#' + this.inputTarget).val();
      if (value !== '') {
        $.get('/composition/reagent?reagent_type=' + this.reagentType + '&term=' + value, function (data) {
          results = $.parseJSON(data);
          if ($.inArray(value, results) === -1) {
            $('#' + that.idPrefix + '-modal').modal('show');
            // Set the lotId value in the modal input
            $('#' + that.idPrefix + '-lot-id-input').val($('#' + that.inputTarget).val());
            // Set the focus on the lotId input
            $('#' + that.idPrefix + '-lot-id-input');
            // Perform the input checks
            that.creationChecks();
            // Reset the target input value
            $('#' + that.inputTarget).val('');
          } else {
            that.checksCallback();
          }
        })
          .fail(function (jqXHR, textStatus, errorThrown) {
            bootstrapAlert(jqXHR.responseText, 'danger');
          });
      } else {
        that.checksCallback();
      }
    },

    /**
     *
     * Auxiliary function to format an input div with feedback
     *
     * @param inputDivName str The id of the div holding the input
     * @param isOk bool Whether the value that contains is valid or not
     *
     **/
    inputCheckFormatter: function(inputDivName, isOk) {
      if (isOk) {
        $('#' + inputDivName).removeClass('has-error').addClass('has-success').find('span').removeClass('glyphicon-remove').addClass('glyphicon-ok');
      } else {
        $('#' + inputDivName).removeClass('has-success').addClass('has-error').find('span').removeClass('glyphicon-ok').addClass('glyphicon-remove');
      }
    },

    /**
     * Performs the needed cheks to enable or disable the ADD button in the modal
     *
     * Checks with the server if the new lot id exists in the system or not and
     * if the reagent initial volume is > 0. If it doesn't exist and the volume
     * is > 0, then it enables the add button, otherwise it is left disabled.
     *
     **/
    creationChecks: function(){
      let that = this;
      var lotId = $('#' + this.idPrefix + '-lot-id-input').val();

      $.get('/composition/reagent?reagent_type=' + this.reagentType + '&term=' + lotId, function (data) {
        results = $.parseJSON(data);
        var lotOk = ($.inArray(lotId, results) === -1);
        that.inputCheckFormatter(that.idPrefix + '-lot-id-div', lotOk);
        $('#' + that.idPrefix + '-btn').prop('disabled', !(lotOk));
      })
        .fail(function (jqXHR, textStatus, errorThrown) {
          bootstrapAlert(jqXHR.responseText, 'danger');
        });
    },

    /**
     *
     * Creates a new reagent lot in the system
     *
     **/
    createReagent: function() {
      let that = this;
      var lotId = $('#' + this.idPrefix + '-lot-id-input').val();
      $.post('/composition/reagent', {'external_id': lotId, 'volume': 1, 'reagent_type': this.reagentType}, function (data) {
        // The reagent has been created
        // Set the value in the target input
        $('#' + that.inputTarget).val(lotId);
        // Close the modal
        $('#' + that.idPrefix + '-modal').modal('hide');
        // Execute the checks callback
        that.checksCallback();
      })
        .fail(function (jqXHR, textStatus, errorThrown) {
          // Show the error
          bootstrapAlert(jqXHR.responseText, 'danger');
          // Hide the modal
          $('#' + that.idPrefix + '-modal').modal('hide');
          // Reset the value
          $('#' + that.inputTarget).val('');
          // Execute the checks callback
          that.checksCallback();
        });
    }
  },

  // VUE function to render the component
  render(createElement) {
    // We need to create the modal here, by calling createElement. Read the VUE.js
    // documentation to learn about this way of creating the template. It is a bit
    // harder to follow, but this is the only way that I could set my own IDs
    // to the different elements on the elements.

    // In the modal, there are three top divs with different classes: modal fade,
    // modal-dialog and modal-content. Inside the modal content there are
    // three different sub-sections: modal-header, modal-body, modal-footer.
    // Create these three subsections:

    // modal-header: contains the button to close the modal and the modal title
    var divModalHeader = createElement(
      'div', // Element type
      {'class': {'modal-header': true}}, // Element attributes
      [ // Children
        // Close button
        createElement(
          'button',
          {'class': {'close': true},
           'attrs': {'type': 'button', 'data-dismiss': 'modal', 'aria-hidden': 'true'}},
          ['x']
        ),
        // Header
        createElement('h3', 'Add new ' + this.reagentType),
      ]
    );

    // modal-body: it contains the two input divs
    // Since we are creating the modal from inner elemnt to outer element,
    // start by creating the input divs

    // External lot id input div
    var divLotId = createElement(
      'div',
      {'class': {'form-group': true, 'has-error': true, 'has-feedback': true}, 'attrs': {'id': this.idPrefix + '-lot-id-div'}},
      [
        // The label
        createElement('label', {'attrs': {'for': this.idPrefix + '-lot-id-input'}}, 'Lot id:'),
        // The input
        createElement('input', {'class': {'form-control': true},
                                'attrs': {'type': 'text', 'id': this.idPrefix + '-lot-id-input'},
                                'on': {'change': this.creationChecks}}),
        // The span
        createElement('span', {'class': {'glyphicon': true, 'glyphicon-remove': true, 'form-control-feedback': true}})
      ]
    );
    // The modal-body div containing the 2 input divs
    var divModalBody = createElement('div', {'class': {'modal-body': true}}, [divLotId]);

    // modal-footer: contains the create reagent button
    var divModalFooter = createElement(
      'div',
      {'class': {'modal-footer': true}},
      [
        // button
        createElement(
          'button',
          {'class': {'btn': true, 'btn-default': true},
           'attrs': {'disabled': true, 'id': this.idPrefix + '-btn'},
           'on': {'click': this.createReagent}},
          'Add')
      ]
    );

    // The modal content div, containing the header, body and footer divs
    var divModalContent = createElement('div', {'class': {'modal-content': true}}, [divModalHeader, divModalBody, divModalFooter]);
    // The modal dialog div, containing the modal content div
    var divModalDialog = createElement('div', {'class': {'modal-dialog': true, 'modal-lg': true}}, [divModalContent]);
    // The modal div, containing the modal dialog div
    var divModal = createElement(
      'div',
      {'class': {'modal': true, 'fade': true},
       'attrs': {'tabindex': -1, 'role': 'dialog', 'id': this.idPrefix + '-modal'}},
      [divModalDialog]);
    return divModal;
  },

  // VUE function called once the component DOM has been generated
  mounted() {
    // Set up the autocomplete in the input target
    $('#' + this.inputTarget).autocomplete({source: this.autocompleteSearchReagent});
    // Set the on change event callback
    $('#' + this.inputTarget).on('change', this.onChangeAutocomplete);
  }
});
