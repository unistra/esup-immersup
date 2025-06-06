function getCookie(name) {
  var cookieValue = null
  if (document.cookie && document.cookie != '') {
    var cookies = document.cookie.split(';')
    for (var i = 0; i < cookies.length; i++) {
      var cookie = django.jQuery.trim(cookies[i])
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) == (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }

  return cookieValue
}

function is_set(obj) {
  return obj !== null && obj !== undefined && obj !== "" && obj !== "None"
}

$(document).ready(function() {

    let query_order = 0
    let results
    let establishment_id = $("#id_establishment").val()
    let has_plugin = false
    let results_text = gettext("Results")
    let select_text = gettext("Select a user ...")

    // Display or hide the search user field
    // only useful on user creation form (not changeform)
    function refresh_search_field() {
      if (!has_plugin || is_set($("#id_is_superuser").val())) {
        $(".field-search").hide()
        $("#id_email").prop("readonly", false);
        $("#id_first_name").prop("readonly", false);
        $("#id_last_name").prop("readonly", false);
      }
      else {
        $(".field-search").show()
        $("#id_email").prop("readonly", true);
        $("#id_first_name").prop("readonly", true);
        $("#id_last_name").prop("readonly", true);
      }
    }

    function get_establishment() {
      let csrftoken = getCookie('csrftoken')

      if(is_set(establishment_id)) {
        $.ajax({
          beforeSend: function (request) {
            request.setRequestHeader('X-CSRFToken', csrftoken)
          },
          url: "/api/establishment/" + establishment_id,
          type: "GET",

          success: function (json) {
            has_plugin = json["data_source_plugin"] !== null
            refresh_search_field()
          }
        })
      }
      else {
        has_plugin = false
        refresh_search_field()
      }
    }

    // init
    refresh_search_field()
    get_establishment()

    $('#id_establishment').on('change', function() {
      establishment_id = this.value
      get_establishment()
    })

    $('#id_search').after(
      '<label id=\'livesearch_label\'>'+results_text+' :</label>' +
          '<select id=\'live_select\' style=\'visibility:hidden\'></select>' +
          '<label id=\'ws_message\' style=\'display:none; width:300px;\'></label>'
    )

    $('#id_search').on('input', function() {
      if(this.value.length >= 2) {
        var csrftoken = getCookie('csrftoken')
        query_order += 1

        $.ajax({
          beforeSend: function (request) {
            request.setRequestHeader('X-CSRFToken', csrftoken)
          },
          url : "/api/get_person",
          type : "POST",
          data : {
            username : this.value,
            establishment_id: establishment_id,
            query_order : query_order
          },

          success : function(json) {
            let msg = json['msg'] !== undefined ? json['msg'] : ""
            let query = json['data'] !== undefined ? json['data'][0] : ""

            if(msg !== '') {
              document.getElementById('ws_message').innerHTML = msg
              $('#ws_message').show()
            }
            else {
              document.getElementById('ws_message').innerHTML = ''
              $('#ws_message').hide()
            }

            // Prevent previous (longer) query from erasing latest one
            if(query >= query_order) {
              results = json['data'] !== undefined ? json['data'].slice(1) : null
              document.getElementById('livesearch_label').style.visibility = 'visible'
              document.getElementById('live_select').style.visibility = 'visible'

              if (results === null) {
                $('#id_email').val('')
                $('#id_first_name').val('')
                $('#id_last_name').val('')
              }
              else {
                $('#live_select').empty().append(
                  '<option value=\'\'>'+select_text+'</option>'
                )
                for (var i = 0; i < results.length; i++) {
                  $('#live_select').append(
                    '<option value=\''+i+'\'>'+results[i]['display_name']+'</option>')
                }
              }
            }
          },

          error : function(e) {
            let obj = JSON.stringify(e)
            console.log('Error : '+obj)
          }
        })
      }
      else {
        document.getElementById('live_select').style.visibility = 'hidden'
        document.getElementById('livesearch_label').style.visibility = 'hidden'

        $('#id_email').val('')
        $('#id_first_name').val('')
        $('#id_last_name').val('')
      }
    })

    $('#live_select').on('change', function (e, json) {
      var optionSelected = $('option:selected', this)
      var valueSelected = this.value

      if(this.value !== '') {
        $('#id_username').val(results[valueSelected]['username'])
        $('#id_email').val(results[valueSelected]['email'])
        $('#id_first_name').val(results[valueSelected]['firstname'])
        $('#id_last_name').val(results[valueSelected]['lastname'])
      }
      else {
        $('#id_username').val('')
        $('#id_email').val('')
        $('#id_first_name').val('')
        $('#id_last_name').val('')
      }
    })
  })

