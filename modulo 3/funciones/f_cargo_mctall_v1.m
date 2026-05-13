function [D,error,file]=f_cargo_mctall(s1,op,file)
%% version 1.1 
% 09/03/18

%clear 
%file='D:\Pacientes\Paciente 1\3Dosim\mctal';
%op=1; 
%s1=[202,219,282]; %matlab; 
%% [219 202 282] MCNP
currentdirectory=pwd;
if isempty(file)
    tipoarchivo='*.*';
    [archivo,directorio]=uigetfile(tipoarchivo,'Select mctall');
    [fid,msm]=fopen(fullfile(directorio,archivo));
     if ~isempty(msm)
        disp(' ')
        disp(msm)
        return 
    end
    file=fullfile(directorio,archivo);
else
    [fid,msm]=fopen(file);
    if ~isempty(msm)
        disp(' ')
        disp(msm)
        disp(' ')
        return 
    end
end

if op==1;busco='tally    1  ';
    elseif op==4;busco='tally    8  ';
    elseif op==2;busco='tally    3  ';
    elseif op==3;busco='tally   18 ';
    elseif op==5;busco='tally   26 ';
    elseif op==6;busco='tally    6 ';
end

tic 
a=0;
while ~feof(fid)
   
     tline = fgetl(fid);
     matches = findstr(tline,busco); 
     %matches = strfind(tline,busco);      
     if matches>0;a=1;end
       
     if a==1
         f=findstr(tline,'f ');
         if ~isempty(f)
             f=tline;
             a2=prod(s1);               
         end
         matches2=findstr(tline,'vals');
         if ~isempty(matches2)
             a1=1;
             resto=mod(a2,4);
             if resto==0
                 A=fscanf(fid,'%g',[8,a2/4]);
             else
                 A=fscanf(fid,'%g',[8,a2/4+1]);
             end
             %A=A';
             break 
         end        
     end    
end   
time=toc;
fclose(fid);

s(1)=s1(2);
s(2)=s1(1);
s(3)=s1(3);
%% dosis
A=A'; 
Dosis=A(:,1:2:8);
Dosis=Dosis';
%Dosis=reshape(Dosis,1,numel(Dosis));
Dosis=Dosis(:); 
Dosis=reshape(Dosis(1:prod(s)),s);

% figure(100)
% for i=1:s1(3)
%     imshow(Dosis(:,:,i),[])
%     colormap(jet)
%     pause(0.01)
% end 

% %% error
e=A(:,2:2:8); %saco los errores del la matriz
e=e';
%e=reshape(e,1,numel(e));
e=e(:); 
e=reshape(e(1:prod(s)),s);

% clear A 
% 
% %%cambiar por un reshape pero me lo modifica
D=zeros(s1);
error=zeros(s1);
%% 
for i=1:s1(3)
     D(:,:,i)=Dosis(:,:,i)';
     error(:,:,i)=e(:,:,i)';
end 
% 
% figure(150)
% for i=1:s(3)
%     imshow(error(:,:,i),[])
%     colormap(jet)
%     pause(0.01)
% end 

cd(currentdirectory);
