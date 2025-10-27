$(document).ready(function() {
  function set_campuses(establishment_id) {
    $.ajax({
      url: '/api/campuses?establishment='+establishment_id,
      type: 'GET',
      success(data) {
        let selected
        let options = '<option value="">---------</option>'
        const campusId = parseInt($('#id_campus').val());
        for (const item of data) {
          const selected = campusId === item.id ? "selected" : "";
          options += `<option ${selected} value="${item.id}">${item.label}</option>`;
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