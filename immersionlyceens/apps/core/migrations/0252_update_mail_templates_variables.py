# Generated by Django 5.0.7 on 2024-07-26 09:09

from django.db import migrations

def update_mail_variables(apps, schema_editor):
    MailTemplateVars = apps.get_model('core', 'MailTemplateVars')
    MailTemplate = apps.get_model('core', 'MailTemplate')

    # Remove creneau.limite_anulation from CPT_DEPOT_PIECE
    try:
        template = MailTemplate.objects.get(code='CPT_DEPOT_PIECE')
        var_code = "{{ creneau.limite_annulation }}"
        tp_var = MailTemplateVars.objects.get(code=var_code)
        template.available_vars.remove(tp_var)
    except Exception as e:
        print(f"cannot add var {var_code} to template 'CPT_DEPOT_PIECE' : {e}")

    # ======================
    # add some variables
    # ======================

    tp_codes = ["CRENEAU_MODIFY_NOTIF", "IMMERSION_ANNUL", "IMMERSION_ANNULATION_INT", "IMMERSION_ANNULATION_STR",
                "IMMERSION_RAPPEL_INT", "IMMERSION_RAPPEL_STR"]

    tp_var_codes = ["{{ cohorte.commentaires }}", "{{ cohorte.etablissementInscrit }}", "{{ cohorte.fichierJoint }}",
                    "{{ cohorte.nbAccompagnateurs }}", "{{ cohorte.nbEleves }}", "{{ cohorte.nbPlaces }}"]

    for tp_code in tp_codes:
        try:
            template = MailTemplate.objects.get(code=tp_code)
            for tp_var_code in tp_var_codes:
                try:
                    tp_var = MailTemplateVars.objects.get(code=tp_var_code)
                    template.available_vars.add(tp_var)
                except Exception as e:
                    print(f"cannot add var {tp_var_code} to template {tp_code} : {e}")
        except Exception as e:
            print(f"cannot add var {tp_var_code} to template {tp_code} : {e}")

    # ======================

    tp_codes = ["IMMERSION_CONFIRM", "IMMERSION_RAPPEL"]

    tp_var_codes = ["{{ cohorte.commentaires }}", "{{ cohorte.etablissementInscrit }}", "{{ cohorte.fichierJoint }}",
                    "{{ cohorte.nbAccompagnateurs }}", "{{ cohorte.nbEleves }}", "{{ cohorte.nbPlaces }}",
                    "{{ destinataire.estCohorte }}", "{{ destinataire.estIndividu }}"]

    for tp_code in tp_codes:
        try:
            template = MailTemplate.objects.get(code=tp_code)
            for tp_var_code in tp_var_codes:
                try:
                    tp_var = MailTemplateVars.objects.get(code=tp_var_code)
                    template.available_vars.add(tp_var)
                except Exception as e:
                    print(f"cannot add var {tp_var_code} to template {tp_code} : {e}")
        except Exception as e:
            print(f"cannot add var {tp_var_code} to template {tp_code} : {e}")

    # ======================

    tp_codes = ["IMMERSION_ANNULATION_INT", "IMMERSION_ANNULATION_STR", "IMMERSION_RAPPEL_INT", "IMMERSION_RAPPEL_STR"]
    tp_var_code = "{{ creneau.listeCohortes }}"

    for tp_code in tp_codes:
        try:
            template = MailTemplate.objects.get(code=tp_code)
            tp_var = MailTemplateVars.objects.get(code=tp_var_code)
            template.available_vars.add(tp_var)
        except Exception as e:
            print(f"cannot add var {tp_var_code} to template {tp_code} : {e}")

    # =======================

    tp_code = "CPT_MIN_CREATE"
    tp_var_code = "{{ educonnect }}"

    try:
        template = MailTemplate.objects.get(code=tp_code)
        tp_var = MailTemplateVars.objects.get(code=tp_var_code)
        template.available_vars.add(tp_var)
    except Exception as e:
        print(f"cannot add var {tp_var_code} to template {tp_code} : {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0251_remove_intro_visit_text'),
    ]

    operations = [

        migrations.RunPython(update_mail_variables),
    ]