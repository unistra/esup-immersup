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
    let item = document.getElementById("template_preview_content")
    item.innerHTML = gettext("<p>Waiting for content</p>")
    $("#template_preview_dialog").dialog("open")
    fetch("/api/mail_template/"+ template_id +"/preview")
        .then(r => r.json())
        .then(response => {
          console.log(response)
          if ( response.data === null ) {
            item.innerHTML = '<h3 class="errornote" style="background: transparent;">' + response.msg + "</h3>"
          } else {
            item.innerHTML = response.data
          }
        })
        .catch(error => {
          item.innerHTML = '<h3 class="errornote" style="background: transparent;">' + gettext("An unexpected error occur") + "</h3>"
        })
  })
})

