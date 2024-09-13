function init_datatable() {
  show_duplicate_btn = typeof show_duplicate_btn === 'boolean' && !show_duplicate_btn ? show_duplicate_btn : true;
  show_delete_btn = typeof show_delete_btn === 'boolean' && !show_delete_btn ? show_delete_btn : true;
  show_modify_btn = typeof show_modify_btn === 'boolean' && !show_modify_btn ? show_modify_btn : true;
  cohorts_only = typeof cohorts_only === 'boolean' && cohorts_only ? cohorts_only : false;
  current_slots_only = typeof current_slots_only === 'boolean' && current_slots_only ? current_slots_only : false;

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

          if (cohorts_only) {
            d.cohorts_only = cohorts_only;
          }

          if (current_slots_only) {
            d.current_slots_only = current_slots_only;
          }

          d.past = $('#filter_past_slots').is(':checked')

          return d
      },
      dataSrc: function (json) {
        if (json['data'] !== undefined && json['data'].length !== 0) {
          return json['data'];
        }
        return [];
      }
    },
    order: [[5, "asc"]],
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
    columns: [
        { data: 'id',
          render: function(data, type, row) {
            let element = ""
            let edit_mode = 0;

            if ( row.structure_code && row.structure_managed_by_me || row.highschool_label && row.highschool_managed_by_me || cohorts_only ) {
              if ( show_duplicate_btn ) {
                element += `<a href="/core/slot/${data}/1" class="btn btn-light btn-sm mr-1" ` +
                           `title="${duplicate_text}"><i class="fa far fa-copy fa-2x centered-icon"></i></a>`;
              }

              // Future slot : edit button
              if(row.is_past === false && show_modify_btn) {
                element += `<a href="/core/slot/${data}" class="btn btn-light btn-sm mr-1" title="${modify_text}"><i class="fa fas fa-pencil fa-2x centered-icon"></i></a>\n`;
              }

              // Future slot and no registration : delete button
              if(row.n_register === 0 && row.n_group_register === 0 && row.is_past === false && show_delete_btn) {
                element += `<button class="btn btn-light btn-sm mr-1" onclick="deleteDialog.data('slot_id', ${data}).dialog('open')" title="${delete_text}"><i class="fa fas fa-trash fa-2x centered-icon"></i></button>\n`;
              }

              // if(row.attendances_value === attendance_to_enter) {
              // Past slot with registrations : can update attendances
              if (cohorts_only === false && row.is_past === true && (row.n_register > 0 || row.n_group_register > 0)) {
                edit_mode = 1
                element += `<button class="btn btn-light btn-sm mr-1" name="edit" onclick="open_modal(${data}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.place})" title="${attendances_text}">` +
                           `<i class='fa fas fa-edit fa-2x centered-icon'></i>` +
                           `</button>`;
              }
              // no attendance to enter : can view registered users or groups
              else if (row.attendances_value === attendance_not_yet || row.attendances_value === attendance_nothing_to_enter || row.n_register > 0 || row.n_group_register > 0) {
                element += `<button class="btn btn-light btn-sm mr-1" name="view" onclick="open_modal(${data}, ${edit_mode}, ${row.n_places}, ${row.allow_individual_registrations}, ${row.allow_group_registrations}, ${row.group_mode}, ${row.n_group_places}, ${row.is_past}, ${row.can_update_registrations}, ${row.place})" title="${registered_text}">` +
                           `<i class='fa fas fa-eye fa-2x centered-icon'></i>` +
                           `</button>`;
              }
              if (cohorts_only === true) {
                element += `<span data-toggle="tooltip" data-html="true" data-contrainer="body" title="${registration_date_limit_txt} : <br>${formatDate(row.registration_limit_date)}">` +
                           `<i class="fa fas fa-calendar pr-2"></i>` +
                           `</span>`;
              }
            }
            return element;
          }
        },
        { data: 'published',
          render: function(data, type, row) {
            return (data) ? yes_text : no_text;
          }
        },
        { data: 'structure_code',
          render: function(data, type, row) {
            if(row.structure_code) {
              return `${row.establishment_code} - ${row.structure_code}`
            }
            else if (row.highschool_label) {
              let city = is_set(row.highschool_city) ? row.highschool_city : no_city_txt
              return `${city} - ${row.highschool_label}`
            }

            return ""
          },
        },
        { data: 'course_training_label' },
        { data: "course_id",
          render: function (data, type, row) {
            let txt = ""
            // TODO: should not happen !!!
            let course_label = is_set(row.course_label) ? row.course_label : ""

            if(type === 'filter') {
              return `${course_label.normalize("NFD").replace(/\p{Diacritic}/gu, "")} (${row.course_type_label})`
            }

            if ( row.structure_code && row.structure_managed_by_me || row.highschool_label && row.highschool_managed_by_me) {
              txt = `<a href="/core/course/${row.course_id}">${row.course_label} (${row.course_type_label})</a>`
            } else {
              txt = `${row.course_label} (${row.course_type_label})`
            }

            return txt
          },
        },
        { data: 'date',
          render: function(data, type, row) {
            return display_slot_date(data, type, row)
          }
        },
        { data: 'n_register',
          render: function(data, type, row) {
            return display_n_register(data, type, row);
          }
        },
        { data: 'campus_label',
          render: function(data, type, row) {
            let campus_label = data
            let building_label = row.building_label
            let room = row.room

            let txt = is_set(campus_label) ? campus_label : ''
            txt += txt !== '' ? '<br>' : ''
            txt += is_set(building_label) ? building_label : ''
            txt += txt !== '' ? '<br>' : ''
            txt += is_set(room) ? room : ''

            if(type === 'filter') {
              return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
            }

            return txt
          }
        },
        { data: 'speaker_list',
          render: function(data, type, row) {
            return display_slot_speakers(data, type, row)
          }
        },
        { data: 'additional_information',
          render: function(data) {
            return display_additional_information(data)
          }
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
        }
    ],
    columnDefs: [
        { defaultContent: '-', targets: '_all' },
    ],

    initComplete: function () {
      var api = this.api();
      var columns_idx = [4, 7, 8]
      var initial_values = { 4: course_label_filter };

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
    let columns_idx = [4, 7, 8]

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

  yadcf.init(dt, [
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
        style_class: "form-control form-control-sm",
        filter_container_id: "managed_by_filter",
        filter_reset_button_text: false,
    },
    {
        column_number: 3,
        filter_default_label: "",
        filter_match_mode: "exact",
        filter_container_id: "training_filter",
        style_class: "form-control form-control-sm",
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
        column_number: 6,
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
  ])

}