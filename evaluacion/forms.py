from django import forms

from .models import Intento


class IngresoForm(forms.Form):
    codigo = forms.CharField(label='Código de la prueba', max_length=10,
                             widget=forms.TextInput(attrs={'autocomplete': 'off', 'autocapitalize': 'characters', 'placeholder': 'Código del docente'}))
    identificador = forms.CharField(label='Tu identificador', max_length=50,
                                    widget=forms.TextInput(attrs={'autocomplete': 'off', 'placeholder': 'Por ejemplo: EST-01'}))
    acompanamiento = forms.ChoiceField(label='¿Cómo vas a responder?', choices=[('', 'Selecciona una opción'), *Intento.Acompanamiento.choices])
    observaciones_apoyo = forms.CharField(label='Observaciones del acompañante (opcional)', required=False, max_length=1000,
                                         widget=forms.Textarea(attrs={'rows': 2}))


class RespuestasForm(forms.Form):
    intento_id = forms.IntegerField(widget=forms.HiddenInput)

    def __init__(self, preguntas, intento_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.intento_esperado = intento_id
        self.fields['intento_id'].initial = intento_id
        for pregunta in preguntas:
            self.fields[f'pregunta_{pregunta["id"]}'] = forms.ChoiceField(
                label=pregunta['enunciado'], choices=list(pregunta['opciones'].items()),
                widget=forms.RadioSelect, error_messages={'required': 'Selecciona una respuesta.'},
            )

    def clean(self):
        datos = super().clean()
        if datos.get('intento_id') != self.intento_esperado:
            raise forms.ValidationError('Esta página corresponde a otro intento. Vuelve a abrir tu prueba.')
        for clave in self.data:
            if clave.startswith('pregunta_') and clave not in self.fields:
                raise forms.ValidationError('El envío contiene una pregunta que no pertenece a esta prueba.')
            if clave in self.fields and hasattr(self.data, 'getlist') and len(self.data.getlist(clave)) != 1:
                raise forms.ValidationError('Selecciona una sola respuesta por pregunta.')
        return datos

    def respuestas(self):
        return {int(nombre.removeprefix('pregunta_')): valor for nombre, valor in self.cleaned_data.items()
                if nombre.startswith('pregunta_')}
