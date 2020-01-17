window.addEventListener('load', function(){hide_forms();});
$(document).on('change', '#id_calendar_mode', hide_forms);


function hide_forms (){
    let elem = $('#id_calendar_mode');
    let year_fields = [
        '.field-year_start_date',
        '.field-year_end_date',
        '.field-year_registration_start_date',
        '.field-year_nb_authorized_immersion',
    ];
    let semester_fields = [
        '.field-semester1_start_date',
        '.field-semester1_end_date',
        '.field-semester1_registration_start_date',
        '.field-semester2_start_date',
        '.field-semester2_end_date',
        '.field-semester2_registration_start_date',
        '.field-registration_start_date_per_semester',
    ];
    if (elem.val() === 'YEAR')
    {
        for ( let i = 0 ; i < semester_fields.length ; i++ ) {
            let field = semester_fields[i];
            $(field).hide();
        }
        for ( let i = 0 ; i < year_fields.length ; i++ ) {
            let field = year_fields[i];
            $(field).show();
        }
    }
    else if (elem.val() === 'SEMESTER')
    {
        for ( let i = 0 ; i < year_fields.length ; i++ ) {
            let field = year_fields[i];
            $(field).hide();
        }
        for ( let i = 0 ; i < semester_fields.length ; i++ ) {
            let field = semester_fields[i];
            $(field).show();
        }
    }
}