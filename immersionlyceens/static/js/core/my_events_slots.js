function init_column_defs() {
  let def = [{
      "defaultContent": "",
      "targets": "_all",
      "className": "all",
    },
    {
      "orderable": false, "targets": 8
    },
  ]
  return def
}

function init_yadcf_filter() {
  let filter = [{
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
    },
    {
      column_number: 7,
      filter_default_label: "",
      style_class: "form-control form-control-sm",
      filter_container_id: "attendances_filter",
      filter_reset_button_text: false,
    },
    {
      column_number: 10,
      filter_default_label: "",
      filter_match_mode: "exact",
      filter_container_id: "groups_filter",
      style_class: "form-control form-control-sm",
      filter_reset_button_text: false,
    },
  ]

  return filter
}

function init_datatable() {
  var columns_idx = [2, 4, 5]

  dt = $('#slots_list').DataTable({
    'processing': false,
    'order': [
      [3, "asc"]
    ],
    'pageLength': 15,
    'lengthMenu': [[5, 10, 25, -1], [5, 10, 25, all_text]],
    'serverSide': false,
    'responsive': false,
    'ajax': {
      url: "/core/utils/slots",
      data: function(d) {
        d.past = $('#filter_past_slots').is(':checked')
        d.courses = false
        d.events = true
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
      { "data": "event_label",
        render: function(data, type, row) {
          let txt = `${data} (${row.event_type_label}) `

          if(type === 'filter') {
            return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
          }

          txt += `<span style="padding-left:5px" data-toggle="tooltip" title="${row.event_description}">
                    <i class="fa fas fa-info-circle fa-2x centered-icon"></i>
                  </span>`

          return txt
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
          let face_to_face = 0
          let remote = 1
          let outside = 2

          if(type === 'filter') {
            if(row.place === face_to_face) {
              txt = `${campus_label} ${building_label} ${row.room}`
            }
            else if(row.place === remote) {
              txt = remote_event_text
            }
            else if(row.place === outside) {
              txt = row.room
            }

            return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
          }

          if(row.place === face_to_face) {
            txt = "<span>"
            txt += is_set(campus_label) ? `${campus_label} </span><br><span>` : ''
            txt += is_set(building_label) ? `${building_label} </span><br><span>` : ''

            return `${txt} ${row.room}</span>`
          }
          else if(row.place === remote) {
            return `<a href="${row.url}" target="_blank">${remote_event_text}</a>`
          }
          else {
            return `<span>${row.room}</span>`
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

          // if(row.attendances_value === 1 && (row.can_update_event_slot || row.can_update_attendances)) {
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
      }
    ],
    "columnDefs": init_column_defs(),

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

  // Filters init
  yadcf.init(dt, init_yadcf_filter());

  dt.on( 'draw', function () {
    $('[data-toggle="tooltip"]').tooltip();
  });
}