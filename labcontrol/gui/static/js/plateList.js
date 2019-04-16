var gPlateInfoByPlateId = {};

function getPlateInfoRequest(plateId, postCheckFunc){
    var request = $.get('/plate/' + plateId + '/', function (data) {
        gPlateInfoByPlateId[plateId] = data;
    })
      .fail(function (jqXHR, textStatus, errorThrown) {
        bootstrapAlert(jqXHR.responseText, 'danger');
        $('#addPlateModal').modal('hide');
      });

    if (typeof(postCheckFunc)!=='undefined'){
        postCheckFunc()
    }

    return request;
}

function requestAndAddPlates(relevantPlateIds, postRequestFunc, postAddFunc){
    // do asynchronous get requests to get info for all the relevant plates
    var requests = [];
    $.each(relevantPlateIds, function(idx, plateId) {
      requests.push(getPlateInfoRequest(plateId, toggleAddPlate));
    });

    // below is basically, "do this when an unknown number of requests have all finished".
    // "$.when takes any number of parameters and resolves when all of these have resolved";
    // see https://stackoverflow.com/a/14777262 for details on construct
    $.when.apply($, requests).then(function() {
        // once all the plate info has been collected,
        // add the plate elements *in the order in which we received the
        // plate ids*, NOT in whatever random order they came back from the
        // asynchronous gets in.
        for (var index = 0; index < relevantPlateIds.length; index++){
            // NB: addPlate is NOT defined in this script.  It is expected
            // to be defined on the page that calls this script.
            addPlate(relevantPlateIds[index])
        }

        if (typeof(postAddFunc)!=='undefined'){
            postAddFunc()
        }
    });
}