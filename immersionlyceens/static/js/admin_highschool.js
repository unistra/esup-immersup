$(document).on('change', 'select#id_department', function() {
  $.ajax({
    url: `/geoapi/cities/${$(this).val()}`,
    type: 'GET',
    success(data) {
      let options = '<option value="">---------</option>'
      for (let i = 0; i < data.length; i++) {
        options += `<option value="${data[i][0]}">${data[i][0]}</option>`
      }
      $('select#id_city').html(options)
    },
  })
  $('select#id_zip_code').html('<option value="">---------</option>')
})

$(document).on('change', 'select#id_city', () => {
  $.ajax({
    url: `/geoapi/zipcodes/${$('select#id_department').val()}/${$('select#id_city').val()}`,
    type: 'GET',
    success(data) {
      var options = '<option value="">---------</option>'
      // console.log(data.length)
      if (data.length === 1) {
        options = `<option value="${data[0][0]}">${data[0][0]}</option>`
      } else {
        for (let i = 0; i < data.length; i++) {
          options += `<option value="${data[i][0]}">${data[i][0]}</option>`
        }

      }
      $('select#id_zip_code').html(options)
    },
  })
})

$(document).on('change', 'select#id_country', function() {
if ($(this).val() != 'FR') {
  $('select#id_department').replaceWith('<input class="form-control" type="text" name="department" id="id_department">')
  $('select#id_city').replaceWith('<input class="form-control" type="text" name="city" id="id_city">')
  $('select#id_zip_code').replaceWith('<input class="form-control" type="text" name="zip_code" id="id_zip_code">')
} else {
  $('#id_department').replaceWith('<select name="department" id="id_department"></select>')
  $('#id_city').replaceWith('<select name="city" id="id_city"></select>')
  $('#id_zip_code').replaceWith('<select name="zip_code" id="id_zip_code"></select>')
  $.ajax({
    url: `/geoapi/departments`,
    type: 'GET',
    success(data) {
      let options = '<option value="">---------</option>'
      for (let i = 0; i < data.length; i++) {
        options += `<option value="${data[i][0]}">${data[i][1]}</option>`
      }
      $('select#id_department').html(options)
    },
  })
  $('select#id_city').html('<option value="">---------</option>')
  $('select#id_zip_code').html('<option value="">---------</option>')
}
})

$(document).on('change', 'input#id_with_convention', function() {
  // Disable convention date fields and datepickers when 'with_convention' is unchecked
  $('#id_convention_start_date').prop("disabled", !$(this).is(':checked'))
  $('#id_convention_start_date').prop("required", $(this).is(':checked'))
  $('#id_convention_end_date').prop("disabled", !$(this).is(':checked'))
  $('#id_convention_end_date').prop("required", $(this).is(':checked'))

   // Hide date fields
  $('.field-convention_start_date').toggle($(this).is(':checked') === true)
  $('.field-convention_end_date').toggle($(this).is(':checked') === true)

  /*
  $('#id_convention_start_date').next('.datetimeshortcuts').toggle($(this).is(':checked') === true)
  $('#id_convention_end_date').next('.datetimeshortcuts').toggle($(this).is(':checked') === true)
  */
})

// init
$(document).ready(function() {
  function toggle_fields() {
    if ($("#id_postbac_immersion").is(':checked')) {
      $("#id_mailing_list").attr("disabled", false)

      $("div.field-badge_html_color").show()
      $("#id_logo").attr("required", false)

      $("div.field-logo").show()
      $("div.field-signature").show()
      $("div.field-certificate_header").show()
      $("div.field-certificate_footer").show()
    } else {
      $("#id_mailing_list").attr("disabled", true)

      $("div.field-badge_html_color").hide()
      $("#id_logo").attr("required", true)

      $("div.field-logo").hide()
      $("div.field-signature").hide()
      $("div.field-certificate_header").hide()
      $("div.field-certificate_footer").hide()
    }
  }
  $("#id_postbac_immersion").change(function () {
    toggle_fields()
  })

  toggle_fields()

  // Hide date fields if convention is not checked
  $('.field-convention_start_date').toggle($('#id_with_convention').is(':checked') === true)
  $('.field-convention_end_date').toggle($('#id_with_convention').is(':checked') === true)
})