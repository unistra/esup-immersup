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
      column_number: 2,
      filter_default_label: "",
      filter_match_mode: "exact",
      style_class: "form-control form-control-sm",
      filter_container_id: "event_filter",
      filter_reset_button_text: false,
    }, {
      column_number: 5,
      filter_type: "text",
      filter_default_label: "",
      style_class: "form-control form-control-sm",
      filter_container_id: "speaker_filter",
      filter_reset_button_text: false,
    }, {
      column_number: 7,
      filter_default_label: "",
      style_class: "form-control form-control-sm",
      filter_container_id: "attendances_filter",
      filter_reset_button_text: false,
    }
  ]

  return filter
}

function init_datatable() {
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
      url: "/api/slots",
      data: function(d) {
        d.past = $('#filter_past_slots').is(':checked')
        d.visits = false
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
      { "data": "managed_by",
        "render": function (data, type, row) {
          let txt = ""

          if(row.establishment) {
            txt = row.establishment.code

            if(row.structure) {
              txt += " - " + row.structure.code;
            }
          }
          else if (row.highschool) {
            txt = row.highschool.city + " - " + row.highschool.label
          }

          return txt
        }
      },
      { "data": "event.label",
        render: function(data, type, row) {
          let txt = data + " (" + row.event.type + ") "
          txt += '<span style="padding-left:5px" data-toggle="tooltip" title="' + row.event.description + '"><i class="fa fas fa-info-circle fa-2x"></i></span>'

          return txt
        }
      },
      {
        "data": "datetime",
        "render": function (data, type, row) {
          if(type === "display" || type === "filter") {
            return "<span>" + row.date + "</span><br><span>" + row.time.start + " - " + row.time.end + "</span>";
          }

          return data;
        }
      },
      {
        "data": "location",
        "render": function (data, type, row) {
          let txt = ""

          if(row.face_to_face) {
              txt += "<span>"
              if (data.campus) {
                  txt += data.campus + "</span><br><span>"
              }
              if (data.building) {
                  txt += data.building + "</span><br><span>"
              }
              return txt + row.room + "</span>";
          }
          else {
            return "<a href='" + row.url + "' target='_blank'>" + remote_event_text + "</a>"
          }
        }
      },
      {
        "data": "speakers",
        "render": function (data, type, row) {
          let txt = "";
          $.each(data, function (name, email) {
            txt += "<a href='mailto:" + email + "'>" + name + "</a><br>";
          });

          if(type === 'filter') {
            return txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
          }

          return txt;
        },
      },
      {
        "data": "",
        render: function(data, type, row) {
          let current = row.n_register;
          let n = row.n_places;
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

          if(row.attendances_value === 1 && (row.can_update_event_slot || row.can_update_attendances)) {
            edit_mode = 1
            msg = "<button class=\"btn btn-light btn-sm mr-4\" name=\"edit\" onclick=\"open_modal("+ row.id +","+ edit_mode +","+row.n_places+","+row.is_past+","+row.can_update_registrations+","+row.face_to_face+")\" title=\""+ attendances_text +"\">" +
                "<i class='fa fas fa-edit fa-2x'></i>" +
                "</button>";
          }
          else if (row.attendances_value !== -1) {
            msg = "<button class=\"btn btn-light btn-sm mr-4\" name=\"view\" onclick=\"open_modal("+ row.id +","+ edit_mode +","+row.n_places+")\" title=\""+ registered_text +"\">" +
                  "<i class='fa fas fa-eye fa-2x'></i>" +
                  "</button>";
          }

          return msg + data;
        }
      },
      {
        "data": "additional_information",
        "render": function (data) {
          if(data){
            return '<span data-toggle="tooltip" title="' + data + '"><i class="fa fas fa-info-circle fa-2x"></i></span>';
          } else {
            return ""
          }
        },
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
      },
    ],
    "columnDefs": init_column_defs(),

    initComplete: function () {
        var api = this.api();

        var columns_idx = [5]

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