// var selected_slots = Array()

function init_datatable() {
  let dt_columns = ""
  let yadcf_filters = ""
  var initial_values = {}
  var columns_idx = []
  let register_date_options = { dateStyle: 'long', timeStyle: 'short' };

  // Columns for cohorts slots pages
  // Here a high school manager we can only view slots opened to cohorts and register his students
  // Do not use for slots management
  dt_columns = [
    {
      data: 'id',
      render: function (data, type, row) {
        let element = ""
        let edit_mode = 0;
        let can_register = row.registration_limit_date_is_past === false
        let badge_class = "badge-info"

        // Future slot : register button
        // TODO: add registration limit date test
        // if (row.is_past === false) {
          element += `<button type="button" class="badge badge-pill badge-primary" name="view" title="${registered_text}" ` +
                       `onclick="open_modal(${data}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.place})">` +
                       `${register_groups_txt}` +
                     `</button>`;
        // }

        if(can_register === false) {
          badge_class = "badge-danger"
        }

        element += `<br><span class="badge badge-pill ${badge_class}">` +
                   `  ${registration_date_limit_txt} : ${formatDate(row.registration_limit_date, register_date_options)}` +
                   `</span>`
        return element;
      }
    },
    {
      data: 'structure_code',
      render: function (data, type, row) {
        if (row.structure_code) {
          return `${row.establishment_code} - ${row.structure_code}`
        }
        else if (row.highschool_label) {
          let city = is_set(row.highschool_city) ? row.highschool_city : no_city_txt
          return `${city} - ${row.highschool_label}`
        }
        else if (row.establishment_code) {
          let txt = row.establishment_code
          txt += is_set(row.structure_code) ? ` - ${row.structure_code}` : ''

          return txt
        }

        return ""
      },
    },
    { data: '',
      render: function (data, type, row) {
        // Course training label if course, else event type label
        if (is_set(row.course_id)) {
          return row.course_training_label
        }
        else {
          return row.event_type_label
        }
      }
    },
    { data: '',
      render: function (data, type, row) {
        // Course label if slot is a course, else event label
        let label = ""

        if (is_set(row.course_id)) {
          label = row.course_label

          if (type === 'filter') {
            return `${label.normalize("NFD").replace(/\p{Diacritic}/gu, "")} (${row.course_type_label})`
          }

          if (row.structure_code && row.structure_managed_by_me || row.highschool_label && row.highschool_managed_by_me) {
            label = `<a href="/core/course/${row.course_id}">${row.course_label} (${row.course_type_label})</a>`
          } else {
            label = `${row.course_label} (${row.course_type_label})`
          }
        }
        else {
          label = row.event_label

          if (type === 'filter') {
            return label.normalize("NFD").replace(/\p{Diacritic}/gu, "")
          }

          label += `<span style="padding-left:5px" data-toggle="tooltip" title="${row.event_description}">` +
                   `<i class="fa fas fa-info-circle fa-2x centered-icon">` +
                   `</i></span>`
        }

        return label
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
        let campus_label = data
        let building_label = row.building_label
        let face_to_face = 0
        let remote = 1
        let outside = 2

        /*
        let room = row.room

        let txt = is_set(campus_label) ? campus_label : ''
        txt += txt !== '' ? '<br>' : ''
        txt += is_set(building_label) ? building_label : ''
        txt += txt !== '' ? '<br>' : ''
        txt += is_set(room) ? room : ''

        if (type === 'filter') {
          return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
        }

        return txt
        */
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
        // Use common slots function
        return display_slot_restrictions(data, type, row)
      }
    }
  ]

  // filters for cohorts slots pages+
  yadcf_filters = [
    {
      column_number: 1,
      filter_default_label: "",
      filter_match_mode: "exact",
      style_class: "form-control form-control-sm",
      filter_container_id: "managed_by_filter",
      filter_reset_button_text: false,
    },
    {
      column_number: 2,
      filter_default_label: "",
      filter_match_mode: "exact",
      filter_container_id: "training_or_type_filter",
      style_class: "form-control form-control-sm",
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

  initial_values = { 3: course_label_filter }
  columns_idx = [3, 5, 6]

  dt = $('#slots_list').DataTable({
    ajax: {
      url: "/core/utils/slots",
      data: function(d) {
          if(is_set(current_establishment_id) || $('#id_establishment').val()) {
            d.establishment_id = current_establishment_id || $('#id_establishment').val();
          }

          if(is_set(current_training_id) || $('#id_training').val()) {
            d.training_id = current_training_id || $('#id_training').val();
          }

          if(is_set(current_structure_id) || $('#id_structure').val()) {
            d.structure_id = current_structure_id || $('#id_structure').val();
          }
          else if(is_set(current_highschool_id) || $('#id_highschool').val()) {
            d.highschool_id = current_highschool_id || $('#id_highschool').val();
          }

          d.events = true;
          d.courses = true;
          d.cohorts_only = true;
          d.highschool_cohorts_registrations_only = true;

          // Retrieve all group slots for this high school
          d.all_slots = true;
          d.past_slots_with_attendances = true;

          return d
      },
      dataSrc: function (json) {
        if (json['data'] !== undefined && json['data'].length !== 0) {
          return json['data'];
        }
        return [];
      }
    },
    order: [[4, "asc"]],
    processing: false,
    serverSide: false,
    responsive: false,
    info: false,
    searching: true,
    searchCols: [
        null,
        null,
        null,
        null,
        { "search": course_label_filter.normalize("NFD").replace(/\p{Diacritic}/gu, "")},
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
      }
    ],

    initComplete: function () {
      var api = this.api();

      columns_idx.forEach(function(col_idx) {
        var column = api.column(col_idx)
        var column_header_id = column.header().id
        var cell = $(`#${column_header_id}`)
        var filter_id = `${column_header_id}_input`
        var title = $(cell).text();
        $(cell).html(title + `<div><input id="${filter_id}" class="form-control form-control-sm" type="text" style="padding: 3px 4px 3px 4px"/></div>`);


        $(`#${filter_id}`).click(function(event) {
          event.stopPropagation()
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
            $(this).attr('title', $(this).val());

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
    }
  });

  // All filters reset action
  $('#filters_reset_all').click(function () {
    yadcf.exResetAllFilters(dt);

    // Clear search inputs
    columns_idx.forEach(function(col_idx) {
      let column = dt.column(col_idx)
      let column_header_id = column.header().id
      let filter_id = `${column_header_id}_input`

      $(`#${filter_id}`).val('')
    })

    dt.columns().search("").draw();
  });

  $('#filter_past_slots').click(function () {
    dt.ajax.reload();
  });

  dt.on( 'draw', function () {
    $('[data-toggle="tooltip"]').tooltip();
  });

  yadcf.init(dt, yadcf_filters)
}