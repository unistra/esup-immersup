function init_datatable() {
  dt = $('#slots_list').DataTable({
    ajax: {
      url: '/api/slots',
      data: function(d) {
          d.visits = true

          if($('#id_establishment').val()) {
            d.establishment_id = $('#id_establishment').val();
          }

          if($('#id_structure').val()) {
            d.structure_id = $('#id_structure').val();
          }

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
    order: [[4, "asc"], [1, "asc"], [2, "asc"], [3, "asc"]],
    processing: false,
    serverSide: false,
    responsive: false,
    info: false,
    search: true,
    searchCols: [
        null,
        { "search": highschool_filter },
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
        { data: 'highschool',
          render: function(data, type, row) {
            return data.city + " - " + data.label;
          },
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
            let establishment_restrictions = ""
            let levels_restrictions = ""
            let span_txt = ""
            let bachelors_types = ""
            let bachelors_mentions = ""
            let bachelors_teachings = ""

            if(data.establishment_restrictions === true) {
              establishment_restrictions += establishments_txt + " :\n"
              data.allowed_establishments.forEach(item => {
                establishment_restrictions += "- " + item + "\n"
              })

              data.allowed_highschools.forEach(item => {
                establishment_restrictions += "- " + item + "\n"
              })
            }

            if(data.levels_restrictions === true) {


              levels_restrictions += levels_txt + " :\n"

              data.allowed_highschool_levels.forEach(item => {
                levels_restrictions += "- " + item + "\n"
              })

              data.allowed_post_bachelor_levels.forEach(item => {
                levels_restrictions += "- " + item + "\n"
              })

              data.allowed_student_levels.forEach(item => {
                levels_restrictions += "- " + item + "\n"
              })
            }

            if(data.bachelors_restrictions === true) {
              if(data.allowed_bachelor_types.length >0){
                bachelors_types += bachelors_txt + " :\n"
                data.allowed_bachelor_types.forEach(item => {
                  bachelors_types += "- " + item + "\n"
                })
              }

              if(data.allowed_bachelor_mentions.length > 0) {
                bachelors_mentions += "\n" + allowed_mentions_txt  + " :\n"
                data.allowed_bachelor_mentions.forEach(item => {
                  bachelors_mentions += "- " + item + "\n"
                })
              }

              if(data.allowed_bachelor_teachings.length > 0) {
                bachelors_teachings += "\n" + allowed_teachings_txt  + " :\n"
                data.allowed_bachelor_teachings.forEach(item => {
                  bachelors_teachings += "- " + item + "\n"
                })
              }
            }

            if (establishment_restrictions.length > 0) {
              span_txt += '<li data-toggle="tooltip" data-container="body" title="' + establishment_restrictions + '"><i class="fa fas fa-info-circle fa-fw"></i> ' + establishments_txt + '</li>'
            }

            if (levels_restrictions.length > 0) {
              span_txt += '<li data-toggle="tooltip" data-container="body" title="' + levels_restrictions + '"><i class="fa fas fa-info-circle fa-fw"></i> ' + levels_txt + '</li>'
            }

            if (bachelors_types.length > 0) {
              span_txt += '<li data-toggle="tooltip" data-container="body" title="' + bachelors_types + '"><i class="fa fas fa-info-circle fa-fw"></i> ' + bachelors_txt + '</li>'
            }

            if (bachelors_mentions.length > 0) {
              span_txt += '<li data-toggle="tooltip" data-container="body" title="' + bachelors_mentions + '"><i class="fa fas fa-info-circle fa-fw"></i> ' + allowed_mentions_txt + '</li>'
            }

            if (bachelors_teachings.length > 0) {
              span_txt += '<li data-toggle="tooltip" data-container="body" title="' + bachelors_teachings + '"><i class="fa fas fa-info-circle fa-fw"></i> ' + allowed_teachings_txt + '</li>'
            }

            return '<ul class="list-unstyled">' + span_txt + '<ul>'
          }
        },
        { data: 'id',
          render: function(data, type, row) {
            if (row['can_update_visit_slot']) {
              let element =
                '  <a href="/core/visit_slot/' + data + '/1" class="btn btn-light btn-sm mr-1" ' +
                '  title="' + duplicate_text + '"><i class="fa far fa-copy fa-2x centered-icon"></i></a>';

              if(row.is_past === false) {
                element += '<a href="/core/visit_slot/' + data + '" class="btn btn-light btn-sm mr-1" title="' + modify_text + '"><i class="fa fas fa-pencil fa-2x centered-icon"></i></a>\n';
              }
              if(row.n_register === 0 && row.is_past === false) {
                element += '<button class="btn btn-light btn-sm mr-1" onclick="deleteDialog.data(\'slot_id\', ' + data + ').dialog(\'open\')" title="' + delete_text + '"><i class="fa fas fa-trash fa-2x centered-icon"></i></button>\n';
              }

              if(row.attendances_value === 1) {
                element += "<button class=\"btn btn-light btn-sm mr-1\" name=\"edit\" onclick=\"open_modal("+ data +","+row.attendances_value+","+row.n_places+","+row.is_past+","+row.can_update_registrations+","+row.face_to_face+")\" title=\"" + attendances_text + "\">" +
                           "<i class='fa fas fa-edit fa-2x centered-icon'></i>" +
                           "</button>";
              }
              else if (row.attendances_value !== -1) {
                element += "<button class=\"btn btn-light btn-sm mr-1\" name=\"view\" onclick=\"open_modal("+ data +","+row.attendances_value+","+row.n_places+","+row.is_past+","+row.can_update_registrations+")\" title=\"" + registered_text + "\">" +
                           "<i class='fa fas fa-eye fa-2x centered-icon'></i>" +
                           "</button>";
              }

              element += "</div>";

              return element;
            } else {
              return '';
            }
          }
        },
    ],
    columnDefs: [{
        defaultContent: '-',
        targets: '_all'
    }, {
      orderable: false,
      targets: [9]
    }],

    initComplete: function () {
      var api = this.api();

      var columns_idx = [3, 5, 6]
      var initial_values = { 3: visit_purpose_filter };

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
    let columns_idx = [3, 5, 6]

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
        filter_container_id: "highschool_filter",
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
    /*
    {
        column_number: 3,
        filter_default_label: "",
        filter_match_mode: "exact",
        style_class: "form-control form-control-sm",
        filter_container_id: "purpose_filter",
        filter_reset_button_text: false,
    },
    */
    {
        column_number: 4,
        filter_type: "text",
        filter_default_label: "",
        filter_container_id: "date_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
    },
    /*
    {
        column_number: 5,
        filter_type: "text",
        filter_default_label: "",
        filter_container_id: "location_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
    },
    {
        column_number: 6,
        filter_type: "text",
        filter_default_label: "",
        filter_container_id: "speakers_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
    },
    */
    {
        column_number: 7,
        filter_type: "text",
        filter_default_label: "",
        filter_container_id: "registration_filter",
        style_class: "form-control form-control-sm",
        filter_reset_button_text: false,
    },
  ])

  if(highschool_filter || managed_by_filter || visit_purpose_filter) {
    let filter_array = Array()

    if(highschool_filter) {
      filter_array.push([1, [highschool_filter]])
    }

    if(managed_by_filter) {
      filter_array.push([2, [managed_by_filter]])
    }

    if(visit_purpose_filter) {
      filter_array.push([3, [visit_purpose_filter]])
    }

    yadcf.exFilterColumn(dt, filter_array);
  }
}