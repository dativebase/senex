$(function(){

    $('a.show-settings-edit-form').click(function() {
        $('div.display-settings-div').hide();
        $('div.edit-settings-div').fadeIn();
    });

    $('a.show-settings-display').click(function() {
        $('div.edit-settings-div').hide();
        $('div.display-settings-div').fadeIn();
    });

    $('input[name=login]').first().focus();

    // This is the long-polling to /senexstatus to see if an install is in
    // progress. TODO: refresh/reload page or update page when install attempt
    // finishes.
    var longPollTimer;
    var longPollURL;
    var longPollInterval = 5000;
    if ($('.installation-in-progress-indicator').is(':visible')) {
        longPollURL = $('.installation-in-progress-indicator').data('url');
        longPoll = function() {
            $.get(longPollURL, function(response) {
                if (!response.installation_in_progress) {
                    clearInterval(longPollTimer);
                    $('.installation-in-progress-indicator').hide();
                }
            });
        }
        longPollTimer = setInterval(longPoll, longPollInterval);
    }
});

