function init_datatable() {
  dt = $('#slots_list').DataTable({
    ajax: {
      url: '/api/slots',
      data: function(d) {
          d.visits = true
          d.highschool_id = $('#id_highschool').val();
          d.highschool_id = current_highschool_id;
          d.past = $('#filter_past_slots').is(':checked')

          return d
      },
      dataSrc: function (json) {
        if (json['data'] !== undefined && json['data'].length !== 0) {
          return json['data'];
        }
        return [];
      },
    },
    order: [[3, "asc"], [1, "asc"], [2, "asc"]],
    processing: false,
    serverSide: false,
    responsive: false,
    info: false,
    search: true,
    searchCols: [
        null,
        { "search": managed_by_filter },
        { "search": visit_purpose_filter.normalize("NFD").replace(/\p{Diacritic}/gu, "")},
        null,
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
        { data: 'published',
          render: function(data, type, row) {
            return (data) ? yes_text : no_text;
          }
        },
        { data: 'establishment',
          render: function(data, type, row) {
            let txt = row.establishment.code

            if(row.structure && row.structure.code) {
              txt += " - " + row.structure.code;
            }

            return txt
          },
        },
        { data: 'visit',
          render: function(data, type, row) {
            let txt = ""
            if (row['can_update_visit_slot']) {
              txt = '<a href="/core/visit/' + data.id + '">' + data.purpose + '</a>'
            } else {
              txt = data.purpose
            }

            if(type === 'filter') {
              return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
            }

            return txt
          }
        },
        { data: 'datetime',
          render: function(data, type, row) {
            if(type === "display" || type === "filter") {
              return "<span>" + row.date + "</span><br><span>" + row.time['start'] + " - " + row.time['end'] + "</span>";
            }

            return data;
          }
        },
        { data: 'room',
          render: function(data, type, row) {
            let value;
            if(row.face_to_face) {
              value = row.room
            }
            else {
              value = remote_visit_text
            }

            if(type === 'filter') {
              return value.normalize("NFD").replace(/\p{Diacritic}/gu, "")
            }

            return value
          }
        },
        { data: 'speakers',
          render: function(data, type, row) {
            let element = '';
            $.each(data, function(name, email) {
              element += '<a href="mailto:' + email + '">' + name + '</a><br>'
            });

            if(type === 'filter') {
              return element.normalize("NFD").replace(/\p{Diacritic}/gu, "")
            }

            return element;
          }
        },
        { data: 'n_register',
          render: function(data, type, row) {
            let current = data;
            let n = row['n_places'];
            element = '<span>' + current + '/' + n + '</span>' +
                '<div class="progress">' +
                '    <div' +
                '       class="progress-bar"' +
                '       role="progressbar"' +
                '       aria-valuenow="' + current + '"' +
                '       aria-valuemin="0"' +
                '       aria-valuemax="' + n + '"' +
                '       style="width: ' + Math.round(current/n * 100) + '%"' +
                '></div>' +
                '</div>';
            return element;
          }
        },
        { "data": "attendances_status",
          "render": function(data, type, row) {
            let msg = "";
            let edit_mode = 0;

            if(row.attendances_value === 1 && (row.can_update_visit_slot || row.can_update_attendances)) {
              edit_mode = 1
              msg = "<button class=\"btn btn-light btn-sm mr-4\" name=\"edit\" onclick=\"open_modal("+ row.id +","+ edit_mode +","+row.n_places+","+row.is_past+","+row.can_update_registrations+","+row.face_to_face+")\" title=\"" + attendances_text + "\">" +
                  "<i class='fa fas fa-edit fa-2x'></i>" +
                  "</button>";
            }
            else if (row.attendances_value !== -1) {
              msg = "<button class=\"btn btn-light btn-sm mr-4\" name=\"view\" onclick=\"open_modal("+ row.id +","+ edit_mode +","+row.n_places+")\" title=\"" + registered_text + "\">" +
                    "<i class='fa fas fa-eye fa-2x'></i>" +
                    "</button>";
            }

            return msg + data;
          }
        },
        { data: 'additional_information',
          render: function(data) {
            if (data) {
              return '<span data-toggle="tooltip" title="' + data + '"><i class="fa fas fa-info-circle fa-2x centered-icon"></i></span>'
            } else {
              return '';
            }
          }
        },
        { data: 'restrictions',
          render: function(data) {
            let txt = ""

            if(data.establishment_restrictions === true) {
              txt += establishments_txt + " :\n"
              data.allowed_establishments.forEach(item => {
                txt += "- " + item + "\n"
              })

              data.allowed_highschools.forEach(item => {
                txt += "- " + item + "\n"
              })
            }

            if(data.levels_restrictions === true) {
              if(txt) txt += "\n"

              txt += levels_txt + " :\n"

              data.allowed_highschool_levels.forEach(item => {
                txt += "- " + item + "\n"
              })

              data.allowed_post_bachelor_levels.forEach(item => {
                txt += "- " + item + "\n"
              })

              data.allowed_student_levels.forEach(item => {
                txt += "- " + item + "\n"
              })
            }

            if (txt) {
              return '<span data-toggle="tooltip" title="' + txt + '"><i class="fa fas fa-info-circle fa-2x centered-icon"></i></span>'
            } else {
              return '';
            }
          }
        }
    ],
    columnDefs: [{
        defaultContent: '-',
        targets: '_all'
    }, {
      orderable: false,
      targets: [8, 9]
    }],

    initComplete: function () {
      var api = this.api();

      var columns_idx = [2, 3, 4, 5]
      var initial_values = { 2: visit_purpose_filter };

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
    let columns_idx = [2, 3, 4, 5]

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

  yadcf.init(dt, [
    {
        column_number: 0,
        filter_default_label: "",
        filter_container_id: "published_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
    },
    {
        column_number: 1,
        filter_default_label: "",
        filter_match_mode: "exact",
        style_class: "form-control form-control-sm",
        filter_container_id: "managed_by_filter",
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
  ])

  if(highschool_filter || managed_by_filter || visit_purpose_filter) {
    let filter_array = Array()

    if(managed_by_filter) {
      filter_array.push([1, [managed_by_filter]])
    }

    if(visit_purpose_filter) {
      filter_array.push([2, [visit_purpose_filter]])
    }

    yadcf.exFilterColumn(dt, filter_array);
  }
}