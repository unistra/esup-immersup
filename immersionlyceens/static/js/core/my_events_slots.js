function init_column_defs() {
  let def = [{
      "defaultContent": "",
      "targets": "_all",
      "className": "all",
    },
    {
      "orderable": false, "targets": 9
    },
  ]

  if(is_highschool_manager) {
    def.push({
      "targets": [ 2 ],
      "visible": false,
      "searchable": false
    })
  }

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
      filter_container_id: "establishment_filter",
      style_class: "form-control form-control-sm",
      filter_reset_button_text: false,
    },
    {
      column_number: 3,
      filter_default_label: "",
      style_class: "form-control form-control-sm",
      filter_container_id: "event_filter",
      filter_reset_button_text: false,
    }, {
      column_number: 6,
      filter_type: "text",
      filter_default_label: "",
      style_class: "form-control form-control-sm",
      filter_container_id: "speaker_filter",
      filter_reset_button_text: false,
    }, {
      column_number: 8,
      filter_default_label: "",
      style_class: "form-control form-control-sm",
      filter_container_id: "attendances_filter",
      filter_reset_button_text: false,
    }
  ]

  if(!is_highschool_manager) {
    filter.push({
      column_number: 2,
      filter_default_label: "",
      filter_container_id: "structure_filter",
      style_class: "form-control form-control-sm",
      filter_reset_button_text: false,
    })
  }

  return filter
}

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
      url: "/api/slots",
      data: function(d) {
        d.past = $('#filter_past_slots').is(':checked')
        d.visits = false
        d.events = true
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
      { "data": "establishment",
        render: function(data, type, row) {
          if(row.establishment) {
            return row.establishment.label
          }
          else if(row.highschool) {
            return row.highschool.label
          }
        },
      },
      { "data": "structure.label" },
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
              return remote_event_text
          }
        }
      },
      {
        "data": "speakers",
        "render": function (data) {
          let txt = "";
          $.each(data, function (name, email) {
            txt += "<a href='mailto:" + email + "'>" + name + "</a><br>";
          });
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
          var msg = "";

          if(row.attendances_value == 1) {
            msg = "<button class=\"btn btn-light btn-sm mr-4\" name=\"edit\" onclick=\"open_modal("+ row.id +","+ row.attendances_value +","+row.n_places+")\" title=\""+ attendances_text +"\">" +
                "<i class='fa fas fa-edit fa-2x'></i>" +
                "</button>";
          }
          else if (row.attendances_value != -1) {
            msg = "<button class=\"btn btn-light btn-sm mr-4\" name=\"view\" onclick=\"open_modal("+ row.id +","+ row.attendances_value +","+row.n_places+")\" title=\""+ registered_text +"\">" +
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
    ],
    "columnDefs": init_column_defs()
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