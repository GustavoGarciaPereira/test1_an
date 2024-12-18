import os
import numpy as np
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from .forms import UploadFileForm
from django.views import View

def xyz_to_fdf(input_xyz, output_fdf):
    """
    Converte um arquivo XYZ para FDF.

    :param input_xyz: Caminho para o arquivo XYZ de entrada.
    :param output_fdf: Caminho para o arquivo FDF de saída.
    """
    # Dicionário de conversão do símbolo atômico para o índice da espécie
    species_map = {
        'C': 1,
        'N': 2,
        'O': 3,
        'H': 4,
        'S': 5
    }

    # Ler o arquivo xyz
    with open(input_xyz, 'r') as f:
        lines = f.readlines()

    # Primeira linha: número de átomos
    num_atoms = int(lines[0].strip())

    # Linhas de coordenadas começam após a linha do número de átomos
    coord_lines = lines[2:]

    # Preparar lista para armazenar dados atômicos
    atoms = []
    for line in coord_lines:
        if line.strip():
            parts = line.split()
            symbol = parts[0]
            x = float(parts[1])
            y = float(parts[2])
            z = float(parts[3])
            if symbol not in species_map:
                raise ValueError(f"Elemento '{symbol}' não está mapeado para nenhuma espécie química.")
            specie_index = species_map[symbol]
            atoms.append((x, y, z, specie_index))

    # Escrever o arquivo de saída .fdf exatamente conforme o gabarito fornecido
    with open(output_fdf, 'w') as out:
        # Cabeçalho do sistema
        out.write("SystemName       Enoxaparin\n")
        out.write("SystemLabel      Enoxaparin\n")
        out.write(f"NumberOfAtoms    {num_atoms}\n")
        out.write("NumberOfSpecies  5\n")
        out.write("%block ChemicalSpeciesLabel\n")
        out.write(" 1   6    C.lda\n")
        out.write(" 2   7    N.lda\n")
        out.write(" 3   8    O.lda\n")
        out.write(" 4   1    H.lda\n")
        out.write(" 5   16   S.lda\n")
        out.write("%endblock ChemicalSpeciesLabel\n\n")

        out.write("LatticeConstant 1.0 Ang\n")
        out.write("%block LatticeVectors\n")
        out.write("  50.000 0.000  0.000\n")
        out.write("  0.000  50.000 0.000\n")
        out.write("  0.000  0.000  50.000\n")
        out.write("%endblock LatticeVectors\n\n")

        out.write("AtomicCoordinatesFormat NotScaledCartesianAng\n")
        out.write("AtomCoorFormatOut   NotScaledCartesianAng\n")
        out.write("%block AtomicCoordinatesAndAtomicSpecies \n")

        # Escrever coordenadas atômicas com índices conforme o gabarito
        # Mantendo 3 espaços iniciais e o mesmo padrão de espaçamento
        for (x, y, z, si) in atoms:
            out.write(f"   {x:10.5f}        {y:10.5f}       {z:10.5f}      {si}\n")

        out.write("%endblock AtomicCoordinatesAndAtomicSpecies\n\n")

        # Demais parâmetros fixos exatamente conforme o gabarito
        out.write("PAO.BasisSize     DZP\n")
        out.write("PAO.EnergyShift   0.05 eV\n")
        out.write("MD.TypeOfRun      CG\n")
        out.write("MD.NumCGsteps     1000\n")
        out.write("MaxSCFIterations  100\n")
        out.write("SpinPolarized true\n")
        out.write("MD.MaxForceTol    0.05 eV/Ang\n")
        out.write("MeshCutoff        200.0 Ry\n")
        out.write("DM.UseSaveDM     true\n")
        out.write("UseSaveData      true\n")
        out.write("MD.UseSaveXV     true\n")
        out.write("MD.UseSaveCG     true\n")
        out.write("DM.MixingWeight   0.10\n")
        out.write("DM.NumberPulay    3\n")
        out.write("WriteCoorXmol\n")
        out.write("WriteMullikenPop 1\n")
        out.write("XC.functional      LDA\n")
        out.write("XC.authors        CA \n")
        out.write("SolutionMethod diagon\n")
        out.write("ElectronicTemperature  80 meV\n")
        out.write("DM.Tolerance         0.1000000000E-02\n")

class ConvertView(View):
    """
    View para processar o upload do arquivo XYZ, converter e retornar o arquivo FDF.
    """
    def get(self, request):
        form = UploadFileForm()
        return render(request, 'converter/upload.html', {'form': form})
    
    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            xyz_file = request.FILES['xyz_file']
            # Certifique-se de que o diretório MEDIA_ROOT existe
            if not os.path.exists(settings.MEDIA_ROOT):
                try:
                    os.makedirs(settings.MEDIA_ROOT)
                except Exception as e:
                    return render(request, 'converter/upload.html', {'form': form, 'error': f"Erro ao criar diretório de mídia: {str(e)}"})
            
            # Salve o arquivo temporariamente
            save_path = os.path.join(settings.MEDIA_ROOT, xyz_file.name)
            try:
                with open(save_path, 'wb+') as destination:
                    for chunk in xyz_file.chunks():
                        destination.write(chunk)
                print(f"Arquivo salvo em: {save_path}")
            except Exception as e:
                return render(request, 'converter/upload.html', {'form': form, 'error': f"Erro ao salvar o arquivo: {str(e)}"})
            
            try:
                # Defina o caminho para o arquivo FDF de saída
                # Renomeie para Enoxaparin.fdf para refletir o sistema convertido
                base_filename = os.path.splitext(xyz_file.name)[0]
                fdf_filename = f"Enoxaparin_{base_filename}.fdf"
                fdf_path = os.path.join(settings.MEDIA_ROOT, fdf_filename)
                
                # Chame a função de conversão
                xyz_to_fdf(save_path, fdf_path)
                print(f"Arquivo FDF gerado em: {fdf_path}")
                
                # Prepare o arquivo para download
                with open(fdf_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{fdf_filename}"'
                
                # Remova os arquivos temporários
                os.remove(save_path)
                os.remove(fdf_path)
                
                return response
            
            except FileNotFoundError:
                # Remova o arquivo salvo se ocorrer um erro
                if os.path.exists(save_path):
                    os.remove(save_path)
                return render(request, 'converter/upload.html', {'form': form, 'error': "Arquivo XYZ não encontrado após o upload."})
            except Exception as e:
                # Remova os arquivos salvos em caso de erro
                if os.path.exists(save_path):
                    os.remove(save_path)
                if os.path.exists(fdf_path):
                    os.remove(fdf_path)
                return render(request, 'converter/upload.html', {'form': form, 'error': f"Erro durante a conversão: {str(e)}"})
        
        return render(request, 'converter/upload.html', {'form': form, 'error': 'Formulário inválido.'})
