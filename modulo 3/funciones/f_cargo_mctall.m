function [D,error,file]=f_cargo_mctall(s1,op,file)
%% version 1.1 
% 09/03/18

%clear 
%file='D:\Pacientes\Paciente 1\3Dosim\Salida\mctal_1';
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
    [fid,msm]=fopen(file,'r');
    if ~isempty(msm)
        disp(' ')
        disp(msm)
        disp(' ')
        return 
    end
end
%% 
% busco='*******';
% error=0;
% 
% %[fid_r,~]=fopen(file,'r');
% 
% linea=0;
% while ~feof(fid_r)
%      linea=linea+1; 
%      tline = fgetl(fid_r);
%      matches = strfind(tline,busco);      
%      if matches>0
%         error=1;  
%         break          
%      end
% end        
% 
% if error==1
%     [fid_w,~]=fopen(file2,'w'); 
%     
%     reemplazo=' 0.0000';
%     cont=0;
%     linea=0;
%     tic
%     while ~feof(fid_r)
%         linea=linea+1;
%         tline = fgetl(fid_r);
%         matches = strfind(tline,busco);
%         if matches>0
%             cont=cont+1;
%             re=strrep(tline,busco,reemplazo);
%             fprintf(fid_w,' s%',re);
%             fprintf(fid_w,' \n');
%         else
%             fprintf(fid_w,'%s',tline);
%             fprintf(fid_w,' \n');
%             
%         end
%     end
%     time=toc;
%     fclose(fid_r);
%     
% else 
%     file_w=file
% end 
%%

if op==1;busco='tally    1  ';
    elseif op==4;busco='tally    8  ';
    elseif op==2;busco='tally    3  ';
    elseif op==3;busco='tally   18 ';
    elseif op==5;busco='tally   26 ';
    elseif op==6;busco='tally    6 ';
end

%tic 
a=0;
a2=prod(s1);

nlinea=1; 
while ~feof(fid)
   
     tline = fgetl(fid);
     nlinea=nlinea+1;
     %matches = findstr(tline,busco); 
     matches = strfind(tline,busco);      
     if matches>0;a=1;end
       
     if a==1         
         matches2=strfind(tline,'vals');
         
         if matches2>0
             resto=mod(a2,4);
             if resto==0
                 A=fscanf(fid,'%f',[8,a2/4]);
             else
                 A=fscanf(fid,'%f',[8,a2/4+1]);
             end
          break 
         end        
     end    
end   
%time=toc;
fclose(fid);


% if numel(A)~=prod(s1) 
%     linea=0;
%     while ~feof(fid)
%          linea=linea+1;
%          tline = fgetl(fid_r);
%          matches = strfind(tline,busco);
%          if matches>0
%             %error=1;
%             disp(' ')
%             disp(' En el archivo mctall hay "*****"')
%             break
%             %return 
%          end
%     end
% end 
%%
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
