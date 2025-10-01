var columns_idx = []

function init_datatable() {
  let _cohorts_only = typeof cohorts_only === 'boolean' && cohorts_only ? cohorts_only : false;
  let _current_slots_only = typeof current_slots_only === 'boolean' && current_slots_only ? current_slots_only : false;
  let dt_columns = ""
  let yadcf_filters = ""
  var initial_values = {}
  var order = []

  if (_cohorts_only) {
    let register_date_options = { dateStyle: 'long', timeStyle: 'short' };

  dt_columns = [
      {
        data: 'id',
        render: function (data, type, row) {
          let element = ""
          let edit_mode = 0;
          let badge_class = "badge-info"
          let valid_restrictions = false

          if(row.allowed_highschools_list.length > 0) {
            let found = row.allowed_highschools_list.find(({id}) => id === parseInt(user_highschool));
            if(is_set(found)) {
              valid_restrictions = true
            }
          }
          else {
            valid_restrictions = true
          }

          let can_register = valid_restrictions && !row.is_past && !row.registration_limit_date_is_past && row.valid_registration_start_date

          // Future slot : register button
          if (can_register) {
            element += `<button type="button" class="badge badge-pill badge-primary" name="view" onclick="open_modal(${data}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.place})" title="${registered_text}">` +
                       `  ${register_groups_txt}` +
                       `</button>`;
          }
          else if(!row.valid_registration_start_date) {
            element += `<span class="badge badge-pill badge-info">` +
                       `  ${registration_start_date_txt} : ${formatDate(row.registration_start_date, register_date_options)}` +
                       `</span>`
          }

          element += element === "" ? "" : "<br>"

          if(row.registration_limit_date_is_past) {
            badge_class = "badge-danger"
          }

          element += `<span class="badge badge-pill ${badge_class}">` +
                     `  ${registration_date_limit_txt} : ${formatDate(row.registration_limit_date, register_date_options)}` +
                     `</span>`

          return element;
        }
      },
      {
        data: 'establishment_code',
        render: function (data, type, row) {
          let txt = ""

          if (data) {
            txt = data
            txt += is_set(row.structure_code) ? ` - ${row.structure_code}` : ''
            return txt
          }
          else if (row.highschool_label) {
            let city = is_set(row.highschool_city) ? row.highschool_city : no_city_txt
            return `${city} - ${row.highschool_label}`
          }
        },
      },
      { data: "event_type_label" },
      {
        data: "event_id",
        render: function (data, type, row) {
          let txt = is_set(row.event_label) ? row.event_label : ""

          if (type === 'filter') {
            return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
          }

          if (row.can_update_event_slot) {
            txt = `<a href="/core/off_offer_event/${data}">${row.event_label}</a>`
          }

          txt += `<span style="padding-left:5px" data-toggle="tooltip" title="${row.event_description}"><i class="fa fas fa-info-circle fa-2x centered-icon"></i></span>`

          return txt
        }
      },
      {
        data: 'date',
        render: function (data, type, row) {
          return display_slot_date(data, type, row)
        }
      },
      {
        data: 'campus_label',
        render: function (data, type, row) {
          let txt = ""
          let campus_label = data
          let building_label = row.building_label
          let face_to_face = 0
          let remote = 1
          let outside = 2

          if (type === 'filter') {
            if (row.place === face_to_face) {
              txt = `${campus_label} ${building_label} ${row.room}`
            }
            else if (row.place === remote) {
              txt = remote_event_text
            }
            else if (row.place === outside) {
              txt = row.room
            }

            return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
          }

          if (row.place === face_to_face) {
            txt = "<span>"
            txt += is_set(campus_label) ? `${campus_label} </span><br><span>` : ''
            txt += is_set(building_label) ? `${building_label} </span><br><span>` : ''

            return `${txt} ${row.room}</span>`
          }
          else if (row.place === remote) {
            // display link only if the group registration is public or the user has already registered a group
            let with_link = `<a href="${row.url}" target="_blank">${remote_event_text}</a>`
            let without_link = `${remote_event_text}`

            if(is_highschool_manager && row.user_has_group_immersions) {
              return with_link
            }

            return without_link
          }
          else {
            return `<span>${row.room}</span>`
          }
        }
      },
      {
        data: 'speaker_list',
        render: function (data, type, row) {
          return display_slot_speakers(data, type, row)
        }
      },
      {
        data: 'n_register',
        render: function (data, type, row) {
          return display_n_register(data, type, row, true);
        }
      },
      {
        data: 'additional_information',
        render: function (data) {
          return display_additional_information(data)
        }
      },
      {
        data: '',
        render: function (data, type, row) {
          return display_slot_restrictions(data, type, row)
        }
      }
    ]

    initial_values = { 3: event_label_filter };
    columns_idx = [3, 5, 6]
    order = [[4, "asc"], [1, "asc"], [2, "asc"], [3, "asc"]]

    yadcf_filters = [
      {
        column_number: 1,
        filter_default_label: "",
        filter_match_mode: "exact",
        filter_container_id: "managed_by_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
      },
      {
        column_number: 2,
        filter_default_label: "",
        filter_match_mode: "exact",
        style_class: "form-control form-control-sm",
        filter_container_id: "event_type_filter",
        filter_reset_button_text: false,
      },
      {
        column_number: 4,
        filter_type: "text",
        filter_default_label: "",
        filter_container_id: "date_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
      },
      {
        column_number: 7,
        filter_type: "text",
        filter_default_label: "",
        filter_container_id: "registration_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
      },
    ]

  } else {
    dt_columns = [
      {
        data: 'id',
        render: function (data, type, row) {
          let element = ""
          let edit_mode = 0;

          if (row['can_update_event_slot']) {
            element += `<a href="/core/off_offer_event_slot/${data}/1" class="btn btn-light btn-sm mr-1" ` +
              `title="${duplicate_text}"><i class="fa far fa-copy fa-2x centered-icon"></i></a>`;

            if (row.is_past === false) {
              element += `<a href="/core/off_offer_event_slot/${data}" class="btn btn-light btn-sm mr-1" title="${modify_text}"><i class="fa fas fa-pencil fa-2x centered-icon"></i></a>\n`;
            }
            if (row.n_register === 0 && row.n_group_register === 0 && row.is_past === false) {
              element += `<button type="button" class="btn btn-light btn-sm mr-1" onclick="deleteDialog.data('slot_id', ${data}).dialog(\'open\')" title="${delete_text}"><i class="fa fas fa-trash fa-2x centered-icon"></i></button>\n`;
            }
          }

          if (row['can_update_attendances']) {
            // Past slot with registrations : can update attendances
            if (row.is_past === true && (row.n_register > 0 || row.n_group_register > 0)) {
              edit_mode = 1;
              element += `<button type="button" class="btn btn-light btn-sm mr-1" name="edit" onclick="open_modal(${data}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.place})" title="${attendances_text}">` +
                `<i class='fa fas fa-edit fa-2x centered-icon'></i>` +
                `</button>`;
            }
            else if (row.attendances_value === attendance_not_yet || row.attendances_value === attendance_nothing_to_enter || row.n_register > 0 || row.n_group_register > 0) {
              element += `<button type="button" class="btn btn-light btn-sm mr-1" name="view" onclick="open_modal(${data}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.place})" title="${registered_text}">` +
                `<i class='fa fas fa-eye fa-2x centered-icon'></i>` +
                `</button>`;
            }
          }

          // We can update registrations when group slot is public or when we manage the high school
          if (((row.can_update_registrations || row.public_group) && _cohorts_only === true) || (row.is_past === true && row.n_register === 0 && row.n_group_register === 0)) {
            element += `<button type="button" class="btn btn-light btn-sm mr-1" name="view" onclick="open_modal(${data}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.place})" title="${registered_text}">` +
              `<i class='fa fas fa-eye fa-2x centered-icon'></i>` +
              `</button>`;
          }

          if (_cohorts_only === true) {
            element += `<span data-toggle="tooltip" data-html="true" data-contrainer="body" title="${registration_date_limit_txt} : <br>${formatDate(row.registration_limit_date)}">` +
              `<i class="fa fas fa-calendar pr-2"></i>` +
              `</span>`;
          }

          return element;
        }
      },
      {
        data: 'published',
        render: function (data, type, row) {
          return (data) ? yes_text : no_text;
        }
      },
      {
        data: 'establishment_code',
        render: function (data, type, row) {
          let txt = ""

          if (data) {
            txt = data
            txt += is_set(row.structure_code) ? ` - ${row.structure_code}` : ''
            return txt
          }
          else if (row.highschool_label) {
            let city = is_set(row.highschool_city) ? row.highschool_city : no_city_txt
            return `${city} - ${row.highschool_label}`
          }
        },
      },
      { data: "event_type_label" },
      {
        data: "event_id",
        render: function (data, type, row) {
          let txt = is_set(row.event_label) ? row.event_label : ""

          if (type === 'filter') {
            return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
          }

          if (row.can_update_event_slot) {
            txt = `<a href="/core/off_offer_event/${data}">${row.event_label}</a>`
          }

          txt += `<span style="padding-left:5px" data-toggle="tooltip" title="${row.event_description}"><i class="fa fas fa-info-circle fa-2x centered-icon"></i></span>`

          return txt
        }
      },
      {
        data: 'date',
        render: function (data, type, row) {
          return display_slot_date(data, type, row)
        }
      },
      {
        data: 'campus_label',
        render: function (data, type, row) {
          let txt = ""
          let campus_label = data
          let building_label = row.building_label
          let face_to_face = 0
          let remote = 1
          let outside = 2

          if (type === 'filter') {
            if (row.place === face_to_face) {
              txt = `${campus_label} ${building_label} ${row.room}`
            }
            else if (row.place === remote) {
              txt = remote_event_text
            }
            else if (row.place === outside) {
              txt = row.room
            }

            return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
          }

          if (row.place === face_to_face) {
            txt = "<span>"
            txt += is_set(campus_label) ? `${campus_label} </span><br><span>` : ''
            txt += is_set(building_label) ? `${building_label} </span><br><span>` : ''

            return `${txt} ${row.room}</span>`
          }
          else if (row.place === remote) {
            return `<a href="${row.url}" target="_blank">${remote_event_text}</a>`
          }
          else {
            return `<span>${row.room}</span>`
          }
        }
      },
      {
        data: 'speaker_list',
        render: function (data, type, row) {
          return display_slot_speakers(data, type, row)
        }
      },
      {
        data: 'n_register',
        render: function (data, type, row) {
          return display_n_register(data, type, row);
        }
      },
      {
        data: 'additional_information',
        render: function (data) {
          return display_additional_information(data)
        }
      },
      {
        data: '',
        render: function (data, type, row) {
          return display_slot_restrictions(data, type, row)
        }
      },
      {
        data: 'allow_group_registrations',
        render: function (data, type, row) {
          if (type === "display") {
            return display_group_informations(row)
          }
          else if (type === "filter" || type === "sort") {
            return set_group_filter(row, type)
          }

          return data
        }
      }
    ]
    initial_values = { 4: event_label_filter };
    columns_idx = [4, 6, 7]
    order = [[5, "asc"], [2, "asc"], [3, "asc"], [4, "asc"]]

    yadcf_filters = [
      {
        column_number: 1,
        filter_default_label: "",
        filter_container_id: "published_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
      },
      {
        column_number: 2,
        filter_default_label: "",
        filter_match_mode: "exact",
        filter_container_id: "managed_by_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
      },
      {
        column_number: 3,
        filter_default_label: "",
        filter_match_mode: "exact",
        style_class: "form-control form-control-sm",
        filter_container_id: "event_type_filter",
        filter_reset_button_text: false,
      },
      {
        column_number: 5,
        filter_type: "text",
        filter_default_label: "",
        filter_container_id: "date_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
      },
      {
        column_number: 8,
        filter_type: "text",
        filter_default_label: "",
        filter_container_id: "registration_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
      },
      {
        column_number: 11,
        filter_default_label: "",
        filter_match_mode: "exact",
        filter_container_id: "groups_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
      },
    ]
  }
  dt = $('#slots_list').DataTable({
    ajax: {
      url: "/core/utils/slots",
      data: function(d) {
        d.events = true
        d.courses = false

        if(is_set(current_establishment_id) || $('#id_establishment').val()) {
          d.establishment_id = current_establishment_id || $('#id_establishment').val();
        }

        if(is_set(current_structure_id) || $('#id_structure').val()) {
          d.structure_id = current_structure_id || $('#id_structure').val();
        }

        if(is_set(current_highschool_id) || $('#id_highschool').val()) {
          d.highschool_id = current_highschool_id || $('#id_highschool').val();
        }

        if(is_set(current_period_id) || $('#id_period').val()) {
          d.period_id = current_period_id || $('#id_period').val();
        }

        if(is_set(_cohorts_only)) {
          d.cohorts_only = _cohorts_only;
        }

        if(is_set(_current_slots_only)) {
          d.current_slots_only = _current_slots_only;
        }

        d.past = $('#filter_past_slots').is(':checked');

        return d;
      },
      dataSrc: function (json) {
        if (json['data'] !== undefined && json['data'].length !== 0) {
          return json['data'];
        }
        return [];
      }
    },
    order: order,
    processing: false,
    serverSide: false,
    responsive: false,
    info: false,
    search: true,
    searchCols: [
        null,
        null,
        { "search": managed_by_filter},
        { "search": event_type_filter},
        { "search": event_label_filter.normalize("NFD").replace(/\p{Diacritic}/gu, "")},
        null,
        null,
        null,
        null,
        null,
    ],
    paging: true,
    ordering: true,
    language: {
      url: language_file
    },
    columns: dt_columns,
    columnDefs: [{
        defaultContent: '-',
        targets: '_all'
    }, {
      "targets": 0,
      "orderable": false,
    }],

    initComplete: function () {
      var api = this.api();

      columns_idx.forEach(function(col_idx) {
        var column = api.column(col_idx);
        var column_header_id = column.header().id;
        var cell = $(`#${column_header_id}`);
        var filter_id = `${column_header_id}_input`;
        var title = $(cell).text();

        $(cell).html(title + `<div><input id="${filter_id}" class="form-control form-control-sm" type="text" style="padding: 3px 4px 3px 4px"/></div>`);

        $(`#${filter_id}`).click(function(event) {
          event.stopPropagation();
        })

        // initial values (is this the best way to set it ?)
        if(col_idx in initial_values) {
          $(`#${filter_id}`).val(initial_values[col_idx]);
        }

        $(`#${filter_id}`)
        .off('keyup change')
        .on('keyup change', function (e) {
            e.stopPropagation();

            // Get the search value
            // $(this).attr('title', $(this).val());

            var cursorPosition = this.selectionStart;

            // Column search with cleaned value
            api
                .column(col_idx)
                .search(
                    this.value !== '' ? this.value.normalize("NFD").replace(/\p{Diacritic}/gu, "") : '',
                    this.value !== '',
                    this.value === ''
                )
                .draw();

            $(this)
                .focus()[0]
                .setSelectionRange(cursorPosition, cursorPosition);
        });
      })

      // yadcf.init(dt, yadcf_filters)
      // set_filter()
    }
  });

  // All filters reset action
  $('#filters_reset_all').click(function () {
    reset_filters()
  })

  $('#filter_past_slots').click(function () {
    dt.ajax.reload();
  });

  dt.on( 'draw', function () {
    $('[data-toggle="tooltip"]').tooltip();
  });

  yadcf.init(dt, yadcf_filters)
  set_filter()
}

function reset_filters() {
  // Duplicated in courses_slots.js
  // Move this in common_slots_list (careful with columns_idx) ?

  yadcf.exResetAllFilters(dt);
  // Clear search inputs
  columns_idx.forEach(function(col_idx) {
    let column = dt.column(col_idx)
    let column_header_id = column.header().id
    let filter_id = `${column_header_id}_input`

    $(`#${filter_id}`).val('')
  })

  dt.columns().search("").draw();
}

function set_filter() {
  let _cohorts_only = typeof cohorts_only === 'boolean' && cohorts_only ? cohorts_only : false;

  if (managed_by_filter || event_type_filter) {
    let filter_array = Array()
    let managed_column = _cohorts_only ? 1 : 2
    let event_type_column = _cohorts_only ? 2 : 3

    if (managed_by_filter) {
      let clean_managed_by_filter = managed_by_filter.replace("(", "\\(").replace(")", "\\)")
      filter_array.push([managed_column, [clean_managed_by_filter]])
    }

    if (event_type_filter) {
      let clean_event_type_filter = event_type_filter.replace("(", "\\(").replace(")", "\\)")
      filter_array.push([event_type_column, [clean_event_type_filter]])
    }

    yadcf.exFilterColumn(dt, filter_array);
  }
}