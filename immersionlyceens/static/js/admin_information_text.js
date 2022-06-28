$(document).ready(function(){
  // Added button before iframe content
  // TODO: ADD STYLE FOR BUTTON
  $('#id_content_iframe').before(
    '<div><button type="button" id="toggle-modal">' +
        gettext('View available documents') +
        '</button></div>'
  )

  // Added some style
  $('#id_content_iframe').css('position', 'relative')
  $('#id_content_iframe').css('top', '20px')
  // $('#template_vars_modal').modal('hide');

  // modal
  $('#docs_list_dialog').dialog({
    autoOpen: false,
    modal: true,
    width: 1000,
  })

  // modal toggle function
  $('#toggle-modal').click(function() {
    $('#docs_list_dialog').dialog('open')
  })
})

