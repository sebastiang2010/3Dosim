
function mat=f_materiales 

%densidad g/cm^3

% H1=1000;
% C6=6000;
% N7=7000;
% O8=8000;
% Na11=11000;
% Mg12=12000;
% P15=15000;
% S16=16000;
% Cl17=17000;
% K19=19000;
% Ca20=20000;
% Fe26=26000;
% I53=53000;

% Materiales en mass fraction 

n=0;

n=n+1;
mat(n,1).Nombre='Aire Dry (near sea level)';
mat(n,1).Id=n; 
mat(n,1).Densidad=0.001205;
mat(n,1).Composicion=[6000, -0.000124;7000, -0.755268; 8000, -0.231481; 18000, -0.012827];
mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));

% n=n+1;
% mat(n,1).Nombre='Skin (ORNL 2007)';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.09;
% mat(n,1).Composicion=[1000, -0.1;6000, -0.204; 7000, -0.042; 8000, -0.645; 11000, -0.002; 15000, -0.001; 16000, -0.002; 17000, -0.003; 19000,-0.001]; 
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));

n=n+1;
mat(n,1).Nombre='Soft Tissue (ICRU 44)';
mat(n,1).Id=n; 
mat(n,1).Densidad=1.06;
mat(n,1).Composicion=[1000, -0.105;6000, -0.143; 7000, -0.034; 8000, -0.708; 11000, -0.002; 15000, -0.003; 16000, -0.003; 17000, -0.002; 19000,-0.003]; 
mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));

n=n+1;
mat(n,1).Nombre='Liver (ICRP 110)';
mat(n,1).Id=n; 
mat(n,1).Densidad=1.05;
mat(n,1).Composicion=[1000, -0.102; 6000, -0.131; 7000, -0.031; 8000, -0.724; 11000, -0.002; 15000,-0.002;16000, -0.003;17000, -0.002;19000,-0.003]; 
mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));

n=n+1;
mat(n,1).Nombre='Tumor';
mat(n,1).Id=n; 
mat(n,1).Densidad=1.05;
mat(n,1).Composicion=[1000, -0.102; 6000, -0.131; 7000, -0.031; 8000, -0.724; 11000, -0.002; 15000,-0.002;16000, -0.003;17000, -0.002;19000,-0.003]; 
mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));


n=n+1;
mat(n,1).Nombre='Lung  (ICRP 110)';
mat(n,1).Id=n; 
mat(n,1).Densidad=0.382;
mat(n,1).Composicion=[1000, -0.103; 6000, -0.107; 7000, -0.022; 8000, -0.644; 11000, -0.01; 15000,-0.002;16000, -0.003;17000, -0.001;19000,-0.002]; 
mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));

n=n+1;
mat(n,1).Nombre='Bone  (ICRP 110)';
mat(n,1).Id=n; 
mat(n,1).Densidad=1.920;
mat(n,1).Composicion=[1000, -0.036; 6000, -0.159; 7000, -0.042; 8000, -0.448; 11000, -0.03;12000,-0.02; 15000,-0.094;16000, -0.003;20000, -0.213]; 
mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));

% n=n+1;
% mat(n,1).Nombre='Adipose Tissue (ICRU 44)';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.02;
% mat(n,1).Composicion=[1000, -0.114; 6000, -0.598; 7000, -0.007; 8000, -0.278; 11000, -0.001; 16000, -0.001;17000, -0.001]; 
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% n=n+1;
% mat(n,1).Nombre='Muscle, Skeletal (ICRU 44)';
% mat(n,1).Id=n;
% mat(n,1).Densidad=1.050;
% mat(n,1).Composicion=[1000, -0.105; 6000, -0.093; 7000, -0.024; 8000, -0.768; 11000, -0.002; 15000, -0.002; 16000,-0.002; 19000,-0.002];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% n=n+1; 
% mat(n,1).Nombre='Bone Cortical (ICRU 44)';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.92;
% mat(n,1).Composicion=[1000, -0.034; 6000, -0.155; 7000, -0.042; 8000, -0.435; 11000, -0.001; 12000, -0.002; 15000, -0.103; 16000, -0.003; 20000, -0.225]; 
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% n=n+1; 
% mat(n,1).Nombre='Stainless carbon (compendium of materials....)';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=7.82;
% mat(n,1).Composicion=[6000,-0.005;26000,-0.995];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% n=n+1; 
% mat(n,1).Nombre='Eyes Id=66-69 ICRP 110';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.05;
% mat(n,1).Composicion=[1000,0.097;6000,0.181;7000,0.053;8000,0.663;11000,0.001;15000,0.001;16000,0.003;17000,0.001];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% 
% mat(201,1).Nombre='Stainless carbon (compendium of materials....)';
% mat(201,1).Id=201; 
% mat(201,1).Densidad=7.82;
% mat(201,1).Composicion=[6000,-0.005;26000,-0.995];
% mat(201,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% % n=n+1; 
% % mat(n,1).Nombre='Anterior nasal passage Id=3-4-7-8-70-71-114-120-121-126-131-134-135-136 (ET1) ICRP 110)';
% % mat(n,1).Id=n; 
% % mat(n,1).Densidad=
% % mat(n,1).Composicion=;
% % mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% % 
% % n=n+1; 
% % mat(n,1).Nombre='Blood vessels Id=9-12 ICRP 110)';
% % mat(n,1).Id=n; 
% % mat(n,1).Densidad=
% % mat(n,1).Composicion=;
% % mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% % 
% % n=n+1; 
% % mat(n,1).Nombre='Cortical bone Id=13-16-19-22-24-28-31-34-37-39-41-43-45-47-49-51-53-55 ICRP 110)';
% % mat(n,1).Id=n; 
% % mat(n,1).Densidad=
% % mat(n,1).Composicion=;
% % mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% % 
% % mat(n,1).Nombre='Cranium Spomgiosa Id=27';
% % mat(n,1).Id=n; 
% % mat(n,1).Densidad=1.245;
% % mat(n,1).Composicion=[];
% % mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% % 
% % mat(n,1).Nombre='Mandible, spongiosa Id=40';
% % mat(n,1).Id=n; 
% mat(n,1).Densidad=1.189;
% mat(n,1).Composicion=[];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% mat(n,1).Nombre='Cartilage Id=57-60';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.100;
% mat(n,1).Composicion=[];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% mat(n,1).Nombre='Brain Id=61';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.050;
% mat(n,1).Composicion=[];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% mat(n,1).Nombre='Lymphatic nodes Id=100-105';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.030;
% mat(n,1).Composicion=[];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% mat(n,1).Nombre='Breast & Residual tissue Id=62-64-116-117-118-119';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.030;
% mat(n,1).Composicion=[];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% mat(n,1).Nombre='Breast & Residual tissue Id=62-64-116-117-118-119';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.030;
% mat(n,1).Composicion=[];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));

% mat(n,1).Nombre='Skin Id=122-123-124-125-141';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.090;
% mat(n,1).Composicion=[];
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));

% n=n+1; 
% mat(n,1).Nombre='Air ID 1 Intercomparison Lung';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.0205e-3;  %g/cm^3
% mat(n,1).Composicion=[7000,-0.755;8000,-0.232;18000,-0.013];% mass fraction
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% n=n+1; 
% mat(n,1).Nombre='Bone ID 255 Intercomparison Lung';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.26;  %g/cm^3
% mat(n,1).Composicion=[1000,-0.0638;6000,-0.472;7000,-0.0212;8000,-0.313;2000,-0.13];% mass fraction
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% n=n+1; 
% mat(n,1).Nombre='Griffith Lung ID 51-102 Intercomparison Lung';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.26;  %g/cm^3
% mat(n,1).Composicion=[1000,-0.08;6000,-0.608;7000,-0.042;8000,-0.249;20000,-0.021];% mass fraction
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% n=n+1;
% mat(n,1).Nombre='Muscle ID 153 Intercomparison Lung';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.26; %g/cm^3
% mat(n,1).Composicion=[1000,-0.903;6000,-0.5937;7000,-0.03;8000,-0.266;20000,-0.017]; % mass fraction 
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% 
% n=n+1;
% mat(n,1).Nombre='Plate ID 204 Intercomparison Lung';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.06;  %g/cm^3
% mat(n,1).Composicion=[1000,-0.0924; 6000,-0.6073;7000,-0.385; 8000,-0.254;20000,-0.078]; % mass fraction
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% n=n+1;
% mat(n,1).Nombre='Polyurethane 1.10 g/cm^3 ID 5-100, Intercomparison Skull';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.10;  %g/cm^3
% mat(n,1).Composicion=[1000,-0.0908; 6000,-0.644; 8000,-0.206]; % mass fraction
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 
% 
% n=n+1; 
% mat(n,1).Nombre='Plaster ID 7-8, Intercomparison Skull';
% mat(n,1).Id=n; 
% mat(n,1).Densidad=1.82;  %g/cm^3
% mat(n,1).Composicion=[1000,-0.023; 8000,-0.558; 20000,-0.233; 16000,-0.186]; % mass fraction
% mat(n,1).sum_comp=abs(sum(mat(n,1).Composicion(:,2)));
% 


