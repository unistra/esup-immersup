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

/*
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
*/
