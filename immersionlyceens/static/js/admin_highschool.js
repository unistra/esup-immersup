// (function($) {
$(document).on('change', "select#id_department", function() {
    $.ajax({
        url: "https://geo.api.gouv.fr/departements/" + $(this).val() + "/communes/?fields=nom",
        type: "GET",
        success: function(data) {
            var options = '<option value="">---------</option>';
            for (var i = 0; i < data.length; i++) {
                options += '<option value="' + data[i].nom.toUpperCase() + '">' + data[i].nom.toUpperCase() + '</option>';
            }
            $("select#id_city").html(options);
        }
    });
    $("select#id_zip_code").html('<option value=""></option>');

});
$(document).on('change', "select#id_city", function() {
    $.ajax({
        url: "https://geo.api.gouv.fr/departements/" + $("select#id_department").val() + "/communes/?fields=nom,codesPostaux",
        type: "GET",
        success: function(data) {
            for (var i = 0; i < data.length; i++) {
                if (data[i].nom.toUpperCase() == $("select#id_city").val()) {
                    var options = '<option value="">---------</option>';
                    var sortedZipCodes = data[i].codesPostaux.sort()
                    if (sortedZipCodes.length == 1) {
                        options = '<option value="' + sortedZipCodes[0] + '">' + sortedZipCodes[0] + '</option>';
                    } else {
                        for (var j = 0; j < sortedZipCodes.length; j++) {
                            options += '<option value="' + sortedZipCodes[j] + '">' + sortedZipCodes[j] + '</option>';
                        }
                    }
                }
            }
            $("select#id_zip_code").html(options);
        }
    });
});
// })(django.jQuery);