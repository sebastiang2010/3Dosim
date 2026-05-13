function [p,file]=f_cargo_mat 

currentdirectory=pwd;
file=[];
tipoarchivo='*.mat';

[archivo,directorio]=uigetfile(tipoarchivo,'Select paciente.mat');
if isequal(archivo,0)||isequal(directorio,0)
    p=[];
    return;
end
cd(directorio);
%file=dir(fullfile(directorio,tipoarchivo)); %carga la etrucuta de archivos

file=[directorio,archivo];
p=load(file);
cd(currentdirectory);
end

