file='D:\Pacientes\Paciente 1\3Dosim\Salida\mctal_error';
file2='D:\Pacientes\Paciente 1\3Dosim\Salida\mctal_ok';

busco='*******';
error=0; 
[fid_r,~]=fopen(file,'r');
[fid_w,~]=fopen(file2,'w'); 

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

if error==1
reemplazo=' 0.0000'; 
cont=0;
linea=0; 
tic 
while ~feof(fid_r)
     linea=linea+1; 
     tline = fgetl(fid_r);
     matches = strfind(tline,busco);      
     if matches>0
         cont=cont+1;
         re=strrep(tline,busco,reemplazo); 
         fprintf(fid_w,' s%',re);
         fprintf(fid_w,' \n'); 
     else 
         fprintf(fid_w,'%s',tline); 
         fprintf(fid_w,' \n'); 
         
     end
end        
time=toc;
fclose(fid_r);
fclose(fid_w);
end 