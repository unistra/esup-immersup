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
  let slot_type_input = document.getElementById("slot_type_input")
  let user_group_input = document.getElementById("user_group_input")
  let local_user_input = document.getElementById("local_user_input")
  let face_to_face_input = document.getElementById("face_to_face_input")

  let item = document.getElementById("template_preview_content")
  item.innerHTML = gettext("<p>Waiting for content</p>")

  let slot_type = slot_type_input.options[slot_type_input.selectedIndex].value
  let user_group = user_group_input.options[user_group_input.selectedIndex].value
  let local_user = local_user_input.options[local_user_input.selectedIndex].value
  let face_to_face = face_to_face_input.options[face_to_face_input.selectedIndex].value

  let url = "/api/mail_template/" + template_id + "/preview"
  url += "?user_group=" + user_group
  url += "&slot_type=" + slot_type
  url += "&local_user=" + local_user
  url += "&face_to_face=" + face_to_face

  fetch(url)
      .then(r => r.json())
      .then(response => {
        if ( response.data === null ) {
          item.innerHTML = '<h3 class="errornote" style="background: transparent;">' + response.msg + "</h3>"
        } else {
          item.innerHTML = response.data
        }
      })
      .catch(error => {
        item.innerHTML = '<h3 class="errornote" style="background: transparent;">' + gettext("An unexpected error occur") + "</h3>"
      })
}

$(document).ready(function() {

  $('#id_body_iframe').before(
    '<div><button type=\'button\' id=\'toggle-modal\' class="button default" style="float: None; padding: 10px;">' +
      gettext('View available variables') +
     '</button>' +
      '<button type=\'button\' id=\'toggle-preview-modal\' class="button default" style="float: None; padding: 10px; margin-left: 20px;">' +
        gettext('Preview') +
     '</button></div>'
  )

  $('#id_body_iframe').css('position', 'relative')
  $('#id_body_iframe').css('top', '20px')
  // $('#template_vars_modal').modal('hide');

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
    // height: 550,
    width: 1000,
  })

  $('#toggle-modal').click(function() {
    $('#template_vars_dialog').dialog('open')
  })

  $("#toggle-preview-modal").click(() => {
    $("#template_preview_dialog").dialog("open")

    load_preview()
  })


  let slot_type_input = document.getElementById("slot_type_input")
  let user_group_input = document.getElementById("user_group_input")
  let local_user_input = document.getElementById("local_user_input")
  let face_to_face_input = document.getElementById("face_to_face_input")
  let change_handler = () => {load_preview()}

  slot_type_input.addEventListener("change", change_handler)
  user_group_input.addEventListener("change", change_handler)
  local_user_input.addEventListener("change", change_handler)
  face_to_face_input.addEventListener("change", change_handler)
})

