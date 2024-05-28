
import functools

from django.db import migrations, models

from immersionlyceens.apps.core.models import InformationText


def population_information_text(apps, schema_editor):

    texts = InformationText.objects.all()

    if not texts.filter(code='INTRO_OFFER_COHORT').exists():
        InformationText.objects.create(
            label="Texte d'introduction pour la page publique des immersions en cohorte",
            code="INTRO_OFFER_COHORT",
            content="<p>Vous pouvez rechercher ici l&#39;ensemble des cours, &eacute;v&egrave;nements ouverts &agrave; l&#39;immersion en cohorte pour l&#39;ensemble des &eacute;tablissements</p>",
            description="Texte d'introduction pour la page publique des immersions en cohorte",
            active=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0234_canceltype_groups_canceltype_students'),
    ]

    operations = [
      migrations.RunPython(population_information_text),
    ]
