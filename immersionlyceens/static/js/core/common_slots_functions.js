function display_additional_information(data) {
    if(data) {
      data = data.replace(/(?:\r\n|\r|\n)/g, '<br>').replace(/"/g, '\'');
      return `<span
        data-toggle="tooltip"
        data-html="true"
        data-contrainer="body"
        title="${data}">
        <i class="fa fas fa-info-circle fa-2x centered-icon"></i>
      </span>`
    }

    return ""
}

function display_n_register(data, type, row, cohorts_only = false) {
    // display registered persons with a progress bar
    let current_students = data;
    let n_places = row['n_places'];

    let n_group_register = row['n_group_register'] || 0;
    let n_group_students = row['n_group_students'] || 0;
    let n_group_guides = row['n_group_guides'] || 0;
    let n_group_total = n_group_students + n_group_guides
    let n_group_places = row['n_group_places'];
    let group_mode = row['group_mode'];

    let allow_individual_registrations = row['allow_individual_registrations'];
    let allow_group_registrations = row['allow_group_registrations'];

    let element = ""

  if (allow_individual_registrations && !cohorts_only) {
        element += '<span>Ind. ' + current_students + '/' + n_places + '</span>' +
            '<div class="progress">' +
            '    <div' +
            '       class="progress-bar"' +
            '       role="progressbar"' +
            '       aria-valuenow="' + current_students + '"' +
            '       aria-valuemin="0"' +
            '       aria-valuemax="' + n_places + '"' +
            '       style="width: ' + Math.round(current_students / n_places * 100) + '%"' +
            '></div>' +
            '</div>';
    }

    if(allow_group_registrations) {
        let full_txt = ""

        if(group_mode === 0 && n_group_register > 0) {
          full_txt = ` - (${group_full_txt})`
        }

        element += `<span>Gr. ${n_group_total}/${n_group_places}${full_txt}</span>` +
            '<div class="progress">' +
            '    <div' +
            '       class="progress-bar"' +
            '       role="progressbar"' +
            '       aria-valuenow="' + n_group_total + '"' +
            '       aria-valuemin="0"' +
            '       aria-valuemax="' + n_group_places + '"' +
            '       style="width: ' + Math.round(n_group_total/n_group_places * 100) + '%"' +
            '></div>' +
            '</div>';
    }

    return element;
  }

function display_slot_speakers(data, type, row) {
    // data : array of objects {email, last_name, first_name}
    let element = '';
    let filter_txt = '';

    $.each(data, function(i, speaker) {
      element += `<a href="mailto:${speaker.email}">${speaker.last_name} ${speaker.first_name}</a><br>`
      filter_txt += `${speaker.last_name} ${speaker.first_name} `
    });

    if(type === 'filter') {
      return filter_txt.normalize("NFD").replace(/\p{Diacritic}/gu, "")
    }

    return element;
}

function display_slot_date(data, type, row, date_options = {year: "numeric", month: "numeric", day: "numeric", weekday: "long"}) {
    // data : datetime serialized by django
    let date = is_set(data) ? data : ''
    let start_time = is_set(row.start_time) ? row.start_time.slice(0, -3) : ''
    let end_time = is_set(row.end_time) ? row.end_time.slice(0, -3) : ''
    let txt = ""

    if(type === "display") {
      txt += date !== '' ? `<span>${formatDate(date, date_options)}</span>` : ''
      txt += txt !== '' ? '<br>' : ''
      txt += start_time !== '' ? `<span>${start_time} - ${end_time}</span>` : ''
      return txt;
    }
    else if(type === 'filter') {
      return `${formatDate(date, date_options)} ${start_time} ${end_time}`
    }

    return data;
}

function display_slot_restrictions(data, type, row) {
    let establishments_restrictions = ""
    let levels_restrictions = ""
    let span_txt = ""
    let bachelors_types = ""
    let bachelors_mentions = ""
    let bachelors_teachings = ""

    if(row.establishments_restrictions === true) {
      establishments_restrictions += `${establishments_txt} :<br>`
      row.allowed_establishments_list.forEach(item => {
        establishments_restrictions += `- ${item}<br>`
      })

      row.allowed_highschools_list.forEach(json => {
        establishments_restrictions += `- ${json['city']} - ${json['label']}<br>`
      })
    }

    if(row.levels_restrictions === true) {
      levels_restrictions += `${levels_txt} :<br>`

      row.allowed_highschool_levels_list.forEach(item => {
        levels_restrictions += `- ${item}<br>`
      })

      row.allowed_post_bachelor_levels_list.forEach(item => {
        levels_restrictions += `- ${item}<br>`
      })

      row.allowed_student_levels_list.forEach(item => {
        levels_restrictions += `- ${item}<br>`
      })
    }

    if(row.bachelors_restrictions === true) {
      if(row.allowed_bachelor_types_list.length > 0) {
        bachelors_types += `${bachelors_txt} : <br>`
        row.allowed_bachelor_types_list.forEach(item => {
          bachelors_types += `- ${item} <br>`
        })
      }

      if(row.allowed_bachelor_mentions_list.length > 0) {
        bachelors_mentions += `${allowed_mentions_txt} :<br>`
        row.allowed_bachelor_mentions_list.forEach(item => {
          bachelors_mentions += `- ${item} <br>`
        })
      }

      if(row.allowed_bachelor_teachings_list.length > 0) {
        bachelors_teachings += `${allowed_teachings_txt} :<br>`
        row.allowed_bachelor_teachings_list.forEach(item => {
          bachelors_teachings += `- ${item} <br>`
        })
      }
    }

    if (establishments_restrictions.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${establishments_restrictions}"><i class="fa fas fa-info-circle fa-fw"></i> ${establishments_txt}</li>`
    }

    if (levels_restrictions.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${levels_restrictions}"><i class="fa fas fa-info-circle fa-fw"></i> ${levels_txt}</li>`
    }

    if (bachelors_types.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${bachelors_types}"><i class="fa fas fa-info-circle fa-fw"></i> ${bachelors_txt}</li>`
    }

    if (bachelors_mentions.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${bachelors_mentions}"><i class="fa fas fa-info-circle fa-fw"></i> ${allowed_mentions_txt}</li>`
    }

    if (bachelors_teachings.length > 0) {
      span_txt += `<li data-toggle="tooltip" data-html="true" data-container="body" title="${bachelors_teachings}"><i class="fa fas fa-info-circle fa-fw"></i> ${allowed_teachings_txt}</li>`
    }

    return `<ul class="list-unstyled">${span_txt}</ul>`
}

function display_group_informations(row) {
  let span = ""

  if(row.allow_individual_registrations === true) {
    let individual_data = `${individual_registrations_txt}
      <br>${places_txt} : ${row.n_places}`

    span += `<span
        data-toggle="tooltip"
        data-html="true"
        data-contrainer="body"
        title="${individual_data}">
        <i class="fa fas fa-user pr-2"></i>
    </span>`
  }

  if(row.allow_group_registrations === true) {
    const ONE_GROUP = 0
    let group_data = `${group_registrations_txt}`
    let details = ''
    let public_private = row.public_group ? public_group_txt : private_group_txt;
    let public_private_icon = row.public_group ? "fa-eye" : "fa-eye-slash"

    if(row.group_mode === ONE_GROUP) {
      group_data += `<br>${mode_txt} : ${one_group_txt}`
    }
    else {
      group_data += `<br>${mode_txt} : ${by_places_txt}`
    }

    group_data += `<br>${places_txt} : ${row.n_group_places}`

    span += `<span
        data-toggle="tooltip"
        data-html="true"
        data-contrainer="body"
        title="${group_data}">
        <i class="fa fas fa-users pr-2"></i>
    </span>`

      span += `<span
        data-toggle="tooltip"
        data-html="true"
        data-contrainer="body"
        title="${public_private}">
        <i class="fa fas ${public_private_icon}"></i>
    </span>`
  }

  return span
}

function set_group_filter(row, type) {
  let group_regs = row.allow_group_registrations ? 2 : 0;
  let indiv_regs = row.allow_individual_registrations ? 1 : 0;
  let sum = group_regs + indiv_regs

  if(type === "sort") {
    return sum
  }

  if (sum === 0) {
    return regs_none_txt;
  }
  else if (sum === 1) {
    return regs_individual_only_txt;
  }
  else if (sum === 2) {
    return regs_groups_only_txt;
  }
  else if (sum === 3) {
    return regs_groups_and_individual_txt;
  }
}