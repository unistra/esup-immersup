function set_fields(period_mode) {
  let REGISTRATION_END_DATE_PERIOD = "0"
  let REGISTRATION_END_DATE_SLOT = "1"

  // Disable convention date fields and datepickers when 'with_convention' is unchecked
  $('#id_registration_end_date').prop("disabled", period_mode === REGISTRATION_END_DATE_SLOT)
  $('#id_registration_end_date').prop("required", period_mode === REGISTRATION_END_DATE_PERIOD)

  $('#id_cancellation_limit_delay').prop("disabled", period_mode === REGISTRATION_END_DATE_SLOT)
  $('#id_cancellation_limit_delay').prop("required", period_mode === REGISTRATION_END_DATE_PERIOD)

  // Hide date fields
  $('.field-registration_end_date').toggle(period_mode === REGISTRATION_END_DATE_PERIOD)
  $('.field-cancellation_limit_delay').toggle(period_mode === REGISTRATION_END_DATE_PERIOD)
}

// init
$(document).ready(function() {

  if($("name=_save")) {
    $("#id_registration_end_date_policy").change(function () {
      set_fields($(this).val())
    })

    set_fields($("#id_registration_end_date_policy").val())
  }
})