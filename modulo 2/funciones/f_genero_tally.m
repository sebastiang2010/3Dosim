function tally_ver=f_genero_tally(archivo,tvoxel,image_size,cell,max_e,tmesh,PatientID,I1,index,n_liver,n_tumor)

tvoxel=quant(tvoxel,0.001); 
tvoxel=tvoxel/10; 
fid=fopen(archivo, 'a+'); %agregar datos al archivo

clc 
%parar=1;
%n=1; 
% while parar==1
%   clc 
%   disp(' ')
%   parar1=1;
%   while parar1==1
%       x(n)=input(' Ingrese la posicion X (MATLAB) del tally de verificacion:  ');
%       if x(n)<1 || x(n)>image_size(1)
%           disp(' ')
%           disp(' Posicion de X no valida');
%       else
%           parar1=-1;
%       end
%   end
% 
%   disp('  ')
%   parar1=1;
%   while parar1==1
%   y(n)=input(' Ingrese la posicion Y (MATLAB) del tally de verificacion:  ');
%       if y(n)<1 || y(n)>image_size(2)
%           disp(' ')
%           disp(' Posicion de Y no valida');
%       else
%           parar1=-1;
%       end
%   end
% 
%   disp('  ')
%   parar1=1;
%   while parar1==1
%   z(n)=input(' Ingrese la posicion Z (MATLAB) del tally de verificacion:  ');
%       if z(n)<1 || z(n)>image_size(3)
%           disp(' ')
%           disp(' Posicion de z no valida');
%       else
%           parar1=-1;
%       end
%   end
% 
% 
%   clc 
%   disp('   ')
%   a=input('  Desea ingresar otro tally de verficacion (~=0-SI // 0=NO):  ');
%   if a==0;parar=-1;end
%   n=n+1; 
% end

fprintf(fid,'c  \n');
fprintf(fid,'c TALLY \n');
fprintf(fid,'c Tally de verificacion \n');
fprintf(fid,'fc18 IDPatient:  %s',PatientID);
fprintf(fid,'  Fecha: ');
fprintf(fid,date);
fprintf(fid,'\n');

tally_ver=zeros(n_tumor+n_liver,3); 

ind=find(I1==index.liver);
[x,y,z]=ind2sub(size(I1),ind);
aleatorio=round(rand(1,n_liver)*size(x,1));

for i=1:n_liver
    x2=x(aleatorio(i)); 
    y2=y(aleatorio(i));
    z2=z(aleatorio(i)); 

    tally_ver(i,:)=[x2;y2;z2]; % MATLAB 

    x1=x2-1;
    y1=y2;
    z1=z2-1;


    %ver si esta flip 
    y1=(image_size(2)-y1); %por que esta flipeado

    a=['c *f',num2str(i),'8  MeV  Higado \n'];
    fprintf(fid,a);
    fprintf(fid,'c Posicion MATLAB ');
    fprintf(fid,' [%g',x2);
    fprintf(fid,' %g',y2 );
    fprintf(fid,' %g] \n',z2);
    a=['*f',num2str(i),'8:e'];
    fprintf(fid,a);
    fprintf(fid,' (%g',max(cell)+1);
    fprintf(fid,' <%g',max(cell)+2);
    fprintf(fid,' [%g',x1);
    fprintf(fid,' %g',y1);
    fprintf(fid,' %g]',z1);
    fprintf(fid,') \n');
end



ind=find(I1==index.tumor);
[x,y,z]=ind2sub(size(I1),ind);
aleatorio=round(rand(1,n_tumor)*size(x,1));
for i=1:n_tumor

    x2=x(aleatorio(i)); 
    y2=y(aleatorio(i));
    z2=z(aleatorio(i)); 

    tally_ver(n_liver+i,:)=[x2;y2;z2];

    x1=x2-1;
    y1=y2;
    z1=z2-1;


    %ver si esta flip 
    y1=(image_size(2)-y1); %por que esta flipeado



    a=['c *f',num2str(i),'8  MeV  Tumor\n'];
    fprintf(fid,a);
    fprintf(fid,'c Posicion MATLAB ');
    fprintf(fid,' [%g',x2);
    fprintf(fid,' %g',y2 );
    fprintf(fid,' %g] \n',z2);
    a=['*f',num2str(n_liver+i),'8:e'];
    fprintf(fid,a);
    fprintf(fid,' (%g',max(cell)+1);
    fprintf(fid,' <%g',max(cell)+2);
    fprintf(fid,' [%g',x1);
    fprintf(fid,' %g',y1);
    fprintf(fid,' %g]',z1);
    fprintf(fid,') \n');
end



b(1)=image_size(1)*tvoxel(1);
b(2)=image_size(2)*tvoxel(2);
b(3)=image_size(3)*tvoxel(3);

a=b./tvoxel'; % numero de separaciones para generar el tally  
a=a-1; 

ok=-1;
if a==image_size-1;ok=1;end

if tmesh(1)==1 %tally 1
    %fprintf(fid,' \n');
    fprintf(fid,'c \n');
    fprintf(fid,'c MESH TALLY 1=F6 \n');
    fprintf(fid,'c MeV/(cm^3 source_particle)  \n');
    %fprintf(fid,'fc1 IDPatient:  %s',PatientID);
    %fprintf(fid,'  Fecha: '); 
    %fprintf(fid,date);
    %fprintf(fid,'\n');
    fprintf(fid,'tmesh \n');
    fprintf(fid,'c \n');
    fprintf(fid,'rmesh1:e   pedep \n');
    fprintf(fid,'cora1  0');
    fprintf(fid,'  %g',a(1));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(1));
    fprintf(fid,'corb1  0');
    fprintf(fid,'  %g',a(2));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(2));
    fprintf(fid,'corc1  0');
    fprintf(fid,'  %g',a(3));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(3));
end
if tmesh(2)==1
    fprintf(fid,'c  \n');
    fprintf(fid,'c MESH TALLY 3=+F6 \n');
    fprintf(fid,'c MeV/(cm^3 source_particle)  \n');
    %fprintf(fid,'fc2 IDPatient:  %s',PatientID);
    %fprintf(fid,'  Fecha: '); 
    %fprintf(fid,date);
    %fprintf(fid,'\n');
    fprintf(fid,'rmesh3 total \n');
    fprintf(fid,'cora3  0');
    fprintf(fid,'  %g',a(1));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(1));
    fprintf(fid,'corb3  0');
    fprintf(fid,'  %g',a(2));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(2));
    fprintf(fid,'corc3  0');
    fprintf(fid,'  %g',a(3));
    fprintf(fid,'i');
    fprintf(fid,'   %g \n',b(3));
    fprintf(fid,'c \n');
end
% fin del mesh tally
fprintf(fid,'endmd \n');
fprintf(fid,'c \n');
if tmesh(1)==1
    fprintf(fid,'ergsh1  0  1e-5');
    fprintf(fid,'  %g',max_e);
    fprintf(fid,' \n');
end
if tmesh(2)==1
    fprintf(fid,'ergsh3  0  1e-5');
    fprintf(fid,'  %g',max_e);
    fprintf(fid,' \n');
end
fprintf(fid,'c  \n');
fclose(fid);

end