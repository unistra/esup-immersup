$(document).ready(function() {
  function set_campuses(establishment_id) {
    $.ajax({
      url: '/api/campuses?establishment='+establishment_id,
      type: 'GET',
      success(data) {
        let selected
        let options = '<option value="">---------</option>'
        for (let i = 0; i < data.length; i++) {
          selected = parseInt($('#id_campus').val()) === data[i]['id'] ? "selected=selected" : ""
          options += `<option ${selected} value="${data[i]['id']}">${data[i]['label']}</option>`
        }
        $('select#id_campus').html(options)
      },
    })
  }

  $('#id_establishment').on('change', function () {
    if(this.value !== undefined) {
      set_campuses(this.value);
    }
  })

  if($('#id_establishment').val() !== undefined) {
    set_campuses($('#id_establishment').val());
  }
})