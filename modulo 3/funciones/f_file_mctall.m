function [file]=f_file_mctall
%UNTITLED Summary of this function goes here
%   Detailed explanation goes here
file=[]; 
currentdirectory=pwd;
if isempty(file)
    tipoarchivo='*.*';
    [archivo,directorio]=uigetfile(tipoarchivo,'Select mctall');
    [~,msm]=fopen(fullfile(directorio,archivo));
     if ~isempty(msm)
        disp(' ')
        disp(msm)
        return 
    end
    file=fullfile(directorio,archivo);
else
    [~,msm]=fopen(file);
    if ~isempty(msm)
        disp(' ')
        disp(msm)
        disp(' ')
        return 
    end
end


cd(currentdirectory);
end

