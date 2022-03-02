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
    '<div><button type=\'button\' id=\'toggle-modal\' class="button default" style="float: left; padding: 10px;">' +
      gettext('View available variables') +
     '</button></div>' +
      '<div><button type=\'button\' id=\'toggle-preview-modal\' class="button default" style="float: left; padding: 10px; margin-left: 20px;">' +
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

  $('#toggle-modal').click(function() {
    $('#template_vars_dialog').dialog('open')
  })
})

