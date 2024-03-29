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
        d.visits = true
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
    'searching': true,
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
    { "data": "establishment_code",
      "render": function (data, type, row) {
        let txt = ""

        if(is_set(data)) {
          txt += data
          txt += is_set(row.structure_code) ? ` - ${row.structure_code}` : ''
        }
        else if (is_set(row.highschool_label)) {
          txt = `${row.highschool_city} - ${row.highschool_label}`
        }

        return txt
      }
    },
    { "data": "highschool_label" },
    { "data": "visit_purpose",
      "render": function(data, type, row) {
        if(type === 'filter') {
          return data.normalize("NFD").replace(/\p{Diacritic}/gu, "")
        }

        return data
      }
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
        let txt = ""
        let campus_label = data
        let building_label = row.building_label

        if(type === 'filter') {
          txt = row.face_to_face ? `${campus_label} ${building_label} ${row.room}` : remote_event_text
          return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
        }

        if(row.face_to_face) {
          txt = "<span>"
          txt += is_set(campus_label) ? `${campus_label} </span><br><span>` : ''
          txt += is_set(building_label) ? `${building_label} </span><br><span>` : ''

          return `${txt} ${row.room}</span>`
        }
        else {
          return `<a href="${row.url}" target="_blank">${remote_event_text}</a>`
        }
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

        if(row.attendances_value === 1 && (row.can_update_visit_slot || row.can_update_attendances)) {
          edit_mode = 1
          msg = `<button class="btn btn-light btn-sm mr-4" name="edit" onclick="open_modal(${row.id}, ${edit_mode}, ${row.n_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.face_to_face})" title="${attendances_text}">` +
                `<i class='fa fas fa-edit fa-2x'></i>` +
                `</button>`;
        }
        else if (row.attendances_value !== -1) {
          msg = `<button class="btn btn-light btn-sm mr-4" name="view" onclick="open_modal(${row.id}, ${edit_mode}, ${row.n_places})" title="${registered_text}">` +
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
  ],
  "columnDefs": [
    {
      "defaultContent": "",
      "targets": "_all",
      "className": "all",
    },
    {
      "orderable": false, "targets": 9
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
    filter_container_id: "managed_by_filter",
    style_class: "form-control form-control-sm",
    filter_reset_button_text: false,
  }, {
    column_number: 2,
    filter_default_label: "",
    filter_match_mode: "exact",
    style_class: "form-control form-control-sm",
    filter_container_id: "high_school_filter",
    filter_reset_button_text: false,
  },
  /*
  {
    column_number: 3,
    filter_default_label: "",
    filter_match_mode: "exact",
    style_class: "form-control form-control-sm",
    filter_container_id: "purpose_filter",
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
  }
  ]);
}