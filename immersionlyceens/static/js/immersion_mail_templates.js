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

const load_preview = () => {
  // get content of ckeditor window
  let content = document.getElementById("id_body").value
  let item = document.getElementById("template_preview_content")
  item.innerHTML = gettext("<p>Waiting for content</p>")

  let url = "/api/mail_template/" + template_id + "/preview"

  // form
  let form = new FormData(document.getElementById("preview_control_form"))
  form.append("body", content)

  fetch(url, {
    method: "POST",
    headers: { "X-CSRFToken": getCookie("csrftoken") },
    body: form
  })
    .then(r => r.json())
    .then(response => {
      if (response.data === null) {
        item.innerHTML = '<h3 class="errornote" style="background: transparent;">' + response.msg + "</h3>"
      } else {
        item.innerHTML = response.data
      }
    })
    .catch(error => {
      item.innerHTML = '<h3 class="errornote" style="background: transparent;">' + gettext("An unexpected error occur") + "</h3>"
    })
}

$(document).ready(function () {
  // Append buttons
  $('#id_body').before(
    '<div><button type=\'button\' id=\'toggle-modal\' class="button default" style="float: None; padding: 10px;">' +
    gettext('View available variables') +
    '</button>' +
    '<button type=\'button\' id=\'toggle-preview-modal\' class="button default" style="float: None; padding: 10px; margin-left: 20px;">' +
    gettext('Preview') +
    '</button></div>'
  )

  $('#id_body').css('position', 'relative')
  $('#id_body').css('top', '20px')

  $('#template_vars_dialog').dialog({
    // dialogClass: "no-close",
    autoOpen: false,
    modal: true,
    // height: 550,
    width: 1000,
  })

  $('#template_preview_dialog').dialog({
    // dialogClass: "no-close",
    autoOpen: false,
    modal: true,
    height: 800,
    width: 1000,
    position: {
            my: "center",
            at: "center",
            of: $('#content')
        },
  })

  $('#toggle-modal').click(function () {
    $('#template_vars_dialog').dialog('open')
  })

  $("#toggle-preview-modal").click(() => {
    $("#template_preview_dialog").dialog("open")
    load_preview()
  })

  // add handler for preview reload
  let change_handler = () => { load_preview() }
  let slot_type_input = document.getElementById("slot_type_input")
  let user_group_input = document.getElementById("user_group_input")
  let local_user_input = document.getElementById("local_user_input")
  let place_input = document.getElementById("place_input")
  let recipient_input = document.getElementById("recipient_input")
  let educonnect_input = document.getElementById("educonnect_input")

  slot_type_input.addEventListener("change", change_handler)
  user_group_input.addEventListener("change", change_handler)
  local_user_input.addEventListener("change", change_handler)
  place_input.addEventListener("change", change_handler)
  recipient_input.addEventListener("change", change_handler)
  educonnect_input.addEventListener("change", change_handler)
})

