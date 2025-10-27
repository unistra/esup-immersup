$(document).on('change', 'select#id_department', function() {
  $.ajax({
    url: `/geoapi/cities/${$(this).val()}`,
    type: 'GET',
    success(data) {
      let options = '<option value="">---------</option>'
      for (const item of data) {
        options += `<option value="${item[0]}">${item[0]}</option>`;
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
      let options = '<option value="">---------</option>'
      // console.log(data.length)
      if (data.length === 1) {
        options = `<option value="${data[0][0]}">${data[0][0]}</option>`
      } else {
        for (const item of data) {
          options += `<option value="${item[0]}">$item[0]}</option>`
        }
      }
      $('select#id_zip_code').html(options)
    },
  })
})

