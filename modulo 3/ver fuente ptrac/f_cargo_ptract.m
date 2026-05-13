function [a,file]=f_cargo_ptract(file)

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

startRow = 12;
endRow = inf;

a=f_importfile(file,startRow, endRow);


cd(currentdirectory);