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

    $(document).ready(function() {
        $('#id_username').after("<label id='livesearch_label'>User found :</label><div id='livesearch' class='vTextField'></div>");
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
                        // document.getElementById("livesearch").innerHTML = "";
                        document.getElementById("livesearch").style.border = "1px solid #A5ACB2";
                        document.getElementById("livesearch_label").style.visibility = "visible";
                        document.getElementById("livesearch").style.visibility = "visible";

                        if (json.length <= 1) {
                            document.getElementById("livesearch").innerHTML="Not found";

                            $('#id_email').val("");
                            $('#id_first_name').val("");
                            $('#id_last_name').val("");
                        }

                        if (json[1]) {
                          $('#id_email').val(json[1]['email']);
                          $('#id_first_name').val(json[1]['firstname']);
                          $('#id_last_name').val(json[1]['lastname']);
                        }

                        for(var i=1; i<json.length; i++) {
                            document.getElementById("livesearch").innerHTML =
                                // json[i]["firstname"] + " " + json[i]["lastname"];
                                json[i]["display_name"];
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
              document.getElementById("livesearch").style.visibility = "hidden";
              document.getElementById("livesearch").innerHTML="";
              document.getElementById("livesearch_label").style.visibility = "hidden";
              document.getElementById("livesearch").style.border="0px";

              $('#id_email').val("");
              $('#id_first_name').val("");
              $('#id_last_name').val("");
            }
        });
    });    
})(django.jQuery)
});