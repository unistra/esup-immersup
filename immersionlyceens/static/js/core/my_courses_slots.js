function init_datatable() {
  dt = $('#slots_list').DataTable({
    'processing': false,
    'order': [
      [4, "asc"]
    ],
    'pageLength': 15,
    'lengthMenu': [[5, 10, 25, -1], [5, 10, 25, all_text]],
    'serverSide': false,
    'responsive': false,
    'ajax': {
      url: "/core/utils/slots",
      data: function(d) {
        d.past = $('#filter_past_slots').is(':checked')
        d.courses = true
        d.events = false
        d.user_slots = true
        return d
      },
      dataSrc: function (json) {
        if (json['data'] !== undefined) {
          return json['data'];
        }
      }
    },
    'search': true,
    'searchCols': [
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
    ],
    'language': {
        url: language_file
    },
    'columns': [
    {
      "data": "published",
      "render": function (data) {
        return (data) ? yes_text : no_text;
      },
    },
    { "data": "structure_code",
      "render": function (data, type, row) {
        let txt = ""
        if(row.establishment_code) {
          txt += row.establishment_code

          if(row.structure_code) {
            txt += " - " + row.structure_code;
          }
        }
        else if (row.highschool_label) {
          let city = is_set(row.highschool_city) ? row.highschool_city : no_city_txt
          txt = city + " - " + row.highschool_label
        }

        return txt
      }
    },
    { "data": "course_training_label" },
    { "data": "course_label",
      "render": function (data, type, row) {
        if(type === 'filter') {
          return data.normalize("NFD").replace(/\p{Diacritic}/gu, "")
        }

        return data
      },
    },
    {
      "data": "date",
      "render": function (data, type, row) {
        return display_slot_date(data, type, row)
      }
    },
    {
      "data": "campus_label",
      "render": function (data, type, row) {
        let campus_label = data
        let building_label = row.building_label

        let txt = is_set(campus_label) ? campus_label : ''
        txt += txt !== '' ? '<br>' : ''
        txt += is_set(building_label) ? building_label : ''
        txt += txt !== '' ? '<br>' : ''
        txt += is_set(row.room) ? row.room : ''

        if(type === 'filter') {
          return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
        }

        return txt
      }
    },
    {
      "data": "speaker_list",
      "render": function (data, type, row) {
        return display_slot_speakers(data, type, row)
      },
    },
    {
      "data": "n_register",
      render: function(data, type, row) {
        return display_n_register(data, type, row);
      }
    },
    { "data": "attendances_status",
      "render": function(data, type, row) {
        let msg = "";
        let edit_mode = 0;

        // if(row.attendances_value === 1 && (row.can_update_course_slot || row.can_update_attendances)) {
        if(row.is_past === true && (row.n_register > 0 || row.n_group_register > 0) && (row.can_update_course_slot || row.can_update_attendances)) {
          edit_mode = 1
          msg = `<button type="button" class="btn btn-light btn-sm mr-4" name="edit" onclick="open_modal(${row.id}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.place})" title="${attendances_text}">` +
                `<i class='fa fas fa-edit fa-2x'></i>` +
                `</button>`;
        }
        // else if (row.attendances_value !== -1) {
        else if (row.attendances_value === attendance_not_yet || row.attendances_value === attendance_nothing_to_enter || row.n_register > 0 || row.n_group_register > 0) {
          msg = `<button type="button" class="btn btn-light btn-sm mr-4" name="view" onclick="open_modal(${row.id}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places})" title="${registered_text}">` +
                `<i class='fa fas fa-eye fa-2x centered-icon'></i>` +
                `</button>`;
        }

        return msg + data;
      }
    },
    {
      "data": "additional_information",
      "render": function (data) {
        return display_additional_information(data)
      },
    },
    { data: '',
      render: function(data, type, row) {
        // Use common slots function
        return display_slot_restrictions(data, type, row)
      }
    },
    { data: 'allow_group_registrations',
      render: function(data, type, row) {
        if(type === "display") {
          return display_group_informations(row)
        }
        else if(type === "filter" || type === "sort") {
          return set_group_filter(row, type)
        }

        return data
      }
    }],
    columnDefs: [{
        defaultContent: '-',
        targets: '_all'
      },
      {
        orderable: false,
        targets: 9
      },
    ],

    initComplete: function () {
        var api = this.api();

        var columns_idx = [3, 6]

        columns_idx.forEach(function(col_idx) {
          var column = api.column(col_idx);
          var column_header_id = column.header().id;
          var cell = $(`#${column_header_id}`);
          var filter_id = `${column_header_id}_input`;
          var title = $(cell).text();

          $(cell).html(title + `<div><input id="${filter_id}" class="form-control form-control-sm" type="text" style="padding: 3px 4px 3px 4px"/></div>`);

          $(`#${filter_id}`).click(function(event) {
            event.stopPropagation()
          })

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
    let columns_idx = [3, 6]

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

  // Filters init
  yadcf.init(dt, [{
      column_number: 0,
      filter_default_label: "",
      filter_container_id: "published_filter",
      style_class: "form-control form-control-sm",
      filter_reset_button_text: false,
    }, {
      column_number: 1,
      filter_default_label: "",
      filter_match_mode: "exact",
      filter_container_id: "structure_filter",
      style_class: "form-control form-control-sm",
      filter_reset_button_text: false,
    },
    {
      column_number: 2,
      filter_default_label: "",
      filter_match_mode: "exact",
      style_class: "form-control form-control-sm",
      filter_container_id: "training_filter",
      filter_reset_button_text: false,
    },
    /*
    {
      column_number: 3,
      filter_default_label: "",
      filter_match_mode: "exact",
      style_class: "form-control form-control-sm",
      filter_container_id: "label_filter",
      filter_reset_button_text: false,
    },
    {
      column_number: 6,
      filter_type: "text",
      filter_default_label: "",
      style_class: "form-control form-control-sm",
      filter_container_id: "speaker_filter",
      filter_reset_button_text: false,
    },
    */
    {
      column_number: 8,
      filter_default_label: "",
      style_class: "form-control form-control-sm",
      filter_container_id: "attendances_filter",
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
  ]);
}