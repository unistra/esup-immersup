function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie != '') {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var cookie = django.jQuery.trim(cookies[i]);
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) == (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }

  return cookieValue;
}
window.addEventListener("load", function() {
  (function($) {
    var query_order = 0;
    var results;
    var results_text = gettext("Results");
    var select_text = gettext("Select a user ...");

    $(document).ready(function() {
        $('#id_username').after(
            "<label id='livesearch_label'>"+results_text+" :</label>" +

              "<select id='live_select' style='visibility:hidden'></select>"

        );

        $('#id_username').on('input', function() {
            if(this.value.length >= 2) {
              var csrftoken = getCookie('csrftoken');
              query_order += 1;

              $.ajax({
                 beforeSend: function (request) {
                   request.setRequestHeader("X-CSRFToken", csrftoken);
                 },

                 url : "/api/get_person",
                 type : "POST",
                 data : {
                   username : this.value,
                   query_order : query_order
                 },

                 success : function(json) {
                    query = json[0];

                    // Prevent previous (longer) query from erasing latest one
                    if(query >= query_order) {
                        document.getElementById("livesearch_label").style.visibility = "visible";
                        document.getElementById("live_select").style.visibility = "visible";

                        if (json.length <= 1) {
                            $('#id_email').val("");
                            $('#id_first_name').val("");
                            $('#id_last_name').val("");
                        }
                        else {
                          results=json;

                          $('#live_select').empty().append(
                              "<option value=''>"+select_text+"</option>"
                          );
                          for (var i = 1; i < json.length; i++) {
                            $('#live_select').append(
                                "<option value='"+i+"'>"+json[i]['display_name']+"</option>");
                          }
                        }
                    }
                 },

                 error : function(e) {
                    obj = JSON.stringify(e);
                    console.log("Error : "+obj);
                 }
              });
            }
            else {
              document.getElementById("live_select").style.visibility = "hidden";
              document.getElementById("livesearch_label").style.visibility = "hidden";

              $('#id_email').val("");
              $('#id_first_name').val("");
              $('#id_last_name').val("");
            }
        });

        $('#live_select').on('change', function (e, json) {
          var optionSelected = $("option:selected", this);
          var valueSelected = this.value;

          if(this.value!='') {
            $('#id_email').val(results[valueSelected]['email']);
            $('#id_first_name').val(results[valueSelected]['firstname']);
            $('#id_last_name').val(results[valueSelected]['lastname']);
          }
          else {
            $('#id_email').val("");
            $('#id_first_name').val("");
            $('#id_last_name').val("");
          }
        });
    });    
  })(django.jQuery)
});