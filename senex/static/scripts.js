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

});

